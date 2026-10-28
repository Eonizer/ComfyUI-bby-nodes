import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Concept List: a read-only preview box showing the items of the selected
// list file (live, as file / file_path change) and the picks from the last run.
// Rows that do nothing in the current setup are hidden (items box when a file
// is used, file dropdown when file_path is set, control_after_generate when seed
// is wired; the seed row stays, it holds the input socket),
// and a pinned node gets a gold outline + 📌. `enabled` is always hidden (bypass
// does the same); old workflows with enabled = false are switched to bypass.

const PREVIEW_URL = "/bby_nodes/concept_list/preview";
const NO_FILE = "(none)";
const PIN_COLOR = "#e0b030";
const MODE_BYPASS = 4;

function widget(node, name) {
	return node.widgets?.find((w) => w.name === name);
}

function pinValue(node) {
	return String(widget(node, "pin")?.value ?? "").trim();
}

function statusLine(node) {
	const status = node.bbyStatus;
	if (status === undefined) return null;
	if (status === "disabled") return "disabled";
	if (status === "skipped") return `skipped (chance ${widget(node, "chance")?.value ?? "?"}%)`;
	if (status === "empty") return "picked: (list is empty)";
	if (status === "pinned") return `📌 pinned: ${node.bbyPicked}`;
	return `picked: ${node.bbyPicked || "(nothing)"}`;
}

function render(node) {
	const parts = [];
	const pin = pinValue(node);
	const status = statusLine(node);
	if (pin && node.bbyStatus !== "pinned") {
		// Not run with this pin yet (or the last run didn't use it).
		parts.push(`📌 pinned: ${pin}`);
		if (status) parts.push(`last run: ${status}`);
	} else if (status) {
		parts.push(status);
	}
	// The list doesn't matter while pinned; only its size is shown.
	if (node.bbyList) parts.push(pin ? node.bbyList.split("\n")[0] : node.bbyList);
	node.bbyPreview.value = parts.join("\n\n");
	app.graph?.setDirtyCanvas(true, false);
}

// Workflows saved before min_count/max_count existed load shifted by one slot:
// seed = "randomize" (shows NaN), enabled = the old seed number. Put them back.
function repairShifted(node) {
	const enabled = widget(node, "enabled");
	const seed = widget(node, "seed");
	const control = widget(node, "control_after_generate");
	if (!seed || Number.isFinite(seed.value)) return;
	const modes = control?.options?.values ?? [];
	if (control && !modes.includes(control.value)) control.value = modes.includes(seed.value) ? seed.value : "randomize";
	seed.value = Number.isFinite(enabled?.value) ? enabled.value : 0;
	if (enabled && typeof enabled.value !== "boolean") enabled.value = true;
}

// Hide rows that have no effect, then fit the node's height to what's left.
function updateLayout(node) {
	const file = widget(node, "file");
	const filePath = String(widget(node, "file_path")?.value ?? "").trim();
	const usesFile = !!filePath || (file && file.value !== NO_FILE);
	const seedInput = node.inputs?.find((i) => i.widget?.name === "seed");
	const seedLinked = seedInput?.link != null;

	const want = {
		items: usesFile,
		file: !!filePath,
		control_after_generate: seedLinked,
		enabled: true,
	};
	let changed = false;
	for (const [name, hide] of Object.entries(want)) {
		const w = widget(node, name);
		if (w && !!w.hidden !== hide) {
			w.hidden = hide;
			changed = true;
		}
	}

	if (changed) fitHeight(node, true);
	render(node);
}

function fitHeight(node, shrink) {
	setTimeout(() => {
		const sz = node.computeSize();
		if (sz[1] > node.size[1] || (shrink && sz[1] < node.size[1])) {
			node.setSize([Math.max(sz[0], node.size[0]), sz[1]]);
			app.graph?.setDirtyCanvas(true, true);
		}
	});
}

async function refresh(node, force = false) {
	const file = widget(node, "file")?.value ?? "";
	const filePath = widget(node, "file_path")?.value ?? "";
	const key = `${file}\n${filePath}`;
	if (key === node.bbyKey && !force) return;
	// Picks from a previous file no longer match what's shown.
	if (node.bbyKey !== undefined && key !== node.bbyKey) {
		node.bbyPicked = undefined;
		node.bbyStatus = undefined;
	}
	node.bbyKey = key;

	const params = new URLSearchParams({ file, file_path: filePath });
	let text;
	try {
		const data = await (await api.fetchApi(`${PREVIEW_URL}?${params}`)).json();
		if (data.error) {
			text = `⚠ ${data.error}`;
		} else if (!data.path) {
			text = "";
		} else {
			const name = data.path.split(/[\\/]/).pop();
			text = `${data.total} items · ${name}\n` + data.items.join("\n");
			if (data.total > data.items.length) text += `\n… ${data.total - data.items.length} more`;
		}
	} catch (e) {
		text = `⚠ preview failed: ${e}`;
	}
	if (node.bbyKey !== key) return; // a newer request has started
	node.bbyList = text;
	render(node);
}

function scheduleRefresh(node) {
	clearTimeout(node.bbyTimer);
	node.bbyTimer = setTimeout(() => refresh(node), 250);
}

function drawCues(node, ctx) {
	if (node.flags?.collapsed) return;
	const titleH = LiteGraph.NODE_TITLE_HEIGHT;
	const [w, h] = node.size;

	if (pinValue(node)) {
		ctx.save();
		ctx.strokeStyle = PIN_COLOR;
		ctx.lineWidth = 2;
		ctx.beginPath();
		ctx.roundRect(-1, -titleH - 1, w + 2, h + titleH + 2, 9);
		ctx.stroke();
		ctx.font = `${Math.round(titleH * 0.55)}px sans-serif`;
		ctx.textAlign = "right";
		ctx.textBaseline = "middle";
		ctx.fillText("📌", w - 8, -titleH / 2);
		ctx.restore();
	}
}

app.registerExtension({
	name: "bby_nodes.ConceptList",
	async beforeRegisterNodeDef(nodeType, nodeData) {
		if (nodeData.name !== "ConceptList") return;

		const onNodeCreated = nodeType.prototype.onNodeCreated;
		nodeType.prototype.onNodeCreated = function () {
			const r = onNodeCreated?.apply(this, arguments);

			const w = ComfyWidgets.STRING(this, "preview", ["STRING", { multiline: true }], app).widget;
			// Display only: not sent to Python, not saved in the workflow.
			w.serialize = false;
			w.options = { ...w.options, serialize: false };
			if (w.inputEl) {
				w.inputEl.readOnly = true;
				w.inputEl.style.opacity = 0.6;
				w.inputEl.placeholder = "Pick a file to preview its items; picks show here after a run.";
			}
			this.bbyPreview = w;

			const node = this;
			const hooks = {
				file: () => (scheduleRefresh(node), updateLayout(node)),
				file_path: () => (scheduleRefresh(node), updateLayout(node)),
				pin: () => updateLayout(node),
			};
			for (const [name, hook] of Object.entries(hooks)) {
				const target = widget(this, name);
				if (!target) continue;
				const callback = target.callback;
				target.callback = function () {
					const cr = callback?.apply(this, arguments);
					hook();
					return cr;
				};
			}

			scheduleRefresh(this);
			setTimeout(() => updateLayout(this));
			return r;
		};

		const onConfigure = nodeType.prototype.onConfigure;
		nodeType.prototype.onConfigure = function () {
			const r = onConfigure?.apply(this, arguments);
			repairShifted(this);
			const enabled = widget(this, "enabled");
			if (enabled?.value === false) {
				enabled.value = true;
				this.mode = MODE_BYPASS;
			}
			scheduleRefresh(this);
			// Links are restored after configure; wait for them before checking the seed input.
			setTimeout(() => updateLayout(this));
			return r;
		};

		const onConnectionsChange = nodeType.prototype.onConnectionsChange;
		nodeType.prototype.onConnectionsChange = function () {
			const r = onConnectionsChange?.apply(this, arguments);
			if (this.bbyPreview) updateLayout(this);
			return r;
		};

		const onDrawForeground = nodeType.prototype.onDrawForeground;
		nodeType.prototype.onDrawForeground = function (ctx) {
			const r = onDrawForeground?.apply(this, arguments);
			drawCues(this, ctx);
			return r;
		};

		const onExecuted = nodeType.prototype.onExecuted;
		nodeType.prototype.onExecuted = function (message) {
			onExecuted?.apply(this, arguments);
			this.bbyPicked = message?.picked?.[0] ?? "";
			this.bbyStatus = message?.status?.[0] ?? "";
			render(this);
			refresh(this, true); // the file may have been edited since
		};
	},
});

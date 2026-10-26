import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

// Concept List: a read-only preview box showing the items of the selected
// list file (live, as file / file_path change) and the picks from the last run.

const PREVIEW_URL = "/bby_nodes/concept_list/preview";

function widget(node, name) {
	return node.widgets?.find((w) => w.name === name);
}

function render(node) {
	const parts = [];
	if (node.bbyPicked !== undefined) parts.push(`picked: ${node.bbyPicked || "(nothing)"}`);
	if (node.bbyList) parts.push(node.bbyList);
	node.bbyPreview.value = parts.join("\n\n");

	requestAnimationFrame(() => {
		const sz = node.computeSize();
		if (sz[1] > node.size[1]) {
			node.setSize([Math.max(sz[0], node.size[0]), sz[1]]);
			app.graph.setDirtyCanvas(true, false);
		}
	});
}

async function refresh(node, force = false) {
	const file = widget(node, "file")?.value ?? "";
	const filePath = widget(node, "file_path")?.value ?? "";
	const key = `${file}\n${filePath}`;
	if (key === node.bbyKey && !force) return;
	// Picks from a previous file no longer match what's shown.
	if (node.bbyKey !== undefined && key !== node.bbyKey) node.bbyPicked = undefined;
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
			for (const name of ["file", "file_path"]) {
				const target = widget(this, name);
				if (!target) continue;
				const callback = target.callback;
				target.callback = function () {
					const cr = callback?.apply(this, arguments);
					scheduleRefresh(node);
					return cr;
				};
			}

			scheduleRefresh(this);
			return r;
		};

		const onConfigure = nodeType.prototype.onConfigure;
		nodeType.prototype.onConfigure = function () {
			const r = onConfigure?.apply(this, arguments);
			scheduleRefresh(this);
			return r;
		};

		const onExecuted = nodeType.prototype.onExecuted;
		nodeType.prototype.onExecuted = function (message) {
			onExecuted?.apply(this, arguments);
			this.bbyPicked = message?.picked?.[0] ?? "";
			render(this);
			refresh(this, true); // the file may have been edited since
		};
	},
});

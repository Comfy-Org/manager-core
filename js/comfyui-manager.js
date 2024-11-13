import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";
import { $el, ComfyDialog } from "../../scripts/ui.js";
import { manager_instance, rebootAPI, migrateAPI, setManagerInstance, show_message } from "./common.js";
import { CustomNodesManager } from "./custom-nodes-manager.js";
import { SnapshotManager } from "./snapshot.js";
import { ModelManager } from "./model-manager.js";

var docStyle = document.createElement('style');
docStyle.innerHTML = `
.comfy-toast {
	position: fixed;
	bottom: 20px;
	left: 50%;
	transform: translateX(-50%);
	background-color: rgba(0, 0, 0, 0.7);
	color: white;
	padding: 10px 20px;
	border-radius: 5px;
	z-index: 1000;
	transition: opacity 0.5s;
}

.comfy-toast-fadeout {
	opacity: 0;
}

#cm-manager-dialog {
	width: 1000px;
	height: 350px;
	box-sizing: content-box;
	z-index: 10000;
	overflow-y: auto;
}

.cb-widget {
	width: 400px;
	height: 25px;
	box-sizing: border-box;
	z-index: 10000;
	margin-top: 10px;
	margin-bottom: 5px;
}

.cb-widget-input {
	width: 305px;
	height: 25px;
	box-sizing: border-box;
}
.cb-widget-input:disabled {
	background-color: #444444;
	color: white;
}

.cb-widget-input-label {
	width: 90px;
	height: 25px;
	box-sizing: border-box;
	color: white;
	text-align: right;
	display: inline-block;
	margin-right: 5px;
}

.cm-menu-container {
	column-gap: 20px;
	display: flex;
	flex-wrap: wrap;
	justify-content: center;
	box-sizing: content-box;
}

.cm-menu-column {
	display: flex;
	flex-direction: column;
	flex: 1 1 auto;
	width: 300px;
	box-sizing: content-box;
}

.cm-title {
	background-color: black;
	text-align: center;
	height: 40px;
	width: calc(100% - 10px);
	font-weight: bold;
	justify-content: center;
	align-content: center;
	vertical-align: middle;
}

#custom-nodes-grid a {
	color: #5555FF;
	font-weight: bold;
	text-decoration: none;
}

#custom-nodes-grid a:hover {
	color: #7777FF;
	text-decoration: underline;
}

.cm-conflicted-nodes-text {
	background-color: #CCCC55 !important;
	color: #AA3333 !important;
	font-size: 10px;
	border-radius: 5px;
	padding: 10px;
}

.cm-warn-note {
	background-color: #101010 !important;
	color: #FF3800 !important;
	font-size: 13px;
	border-radius: 5px;
	padding: 10px;
	overflow-x: hidden;
	overflow: auto;
}

.cm-info-note {
	background-color: #101010 !important;
	color: #FF3800 !important;
	font-size: 13px;
	border-radius: 5px;
	padding: 10px;
	overflow-x: hidden;
	overflow: auto;
}
`;

document.head.appendChild(docStyle);

var update_comfyui_button = null;
var switch_comfyui_button = null;
var fetch_updates_button = null;
var update_all_button = null;
let share_option = 'all';

// copied style from https://github.com/pythongosssss/ComfyUI-Custom-Scripts
const style = `
#workflowgallery-button {
	width: 310px;
	height: 27px;
	padding: 0px !important;
	position: relative;
	overflow: hidden;
	font-size: 17px !important;
}
#cm-nodeinfo-button {
	width: 310px;
	height: 27px;
	padding: 0px !important;
	position: relative;
	overflow: hidden;
	font-size: 17px !important;
}
#cm-manual-button {
	width: 310px;
	height: 27px;
	position: relative;
	overflow: hidden;
}

.cm-button {
	width: 310px;
	height: 30px;
	position: relative;
	overflow: hidden;
	font-size: 17px !important;
}

.cm-button-red {
	width: 310px;
	height: 30px;
	position: relative;
	overflow: hidden;
	font-size: 17px !important;
	background-color: #500000 !important;
	color: white !important;
}


.cm-button-orange {
	width: 310px;
	height: 30px;
	position: relative;
	overflow: hidden;
	font-size: 17px !important;
	font-weight: bold;
	background-color: orange !important;
	color: black !important;
}

.cm-experimental-button {
	width: 290px;
	height: 30px;
	position: relative;
	overflow: hidden;
	font-size: 17px !important;
}

.cm-experimental {
	width: 310px;
	border: 1px solid #555;
	border-radius: 5px;
	padding: 10px;
	align-items: center;
	text-align: center;
	justify-content: center;
	box-sizing: border-box;
}

.cm-experimental-legend {
	margin-top: -20px;
	margin-left: 50%;
	width:auto;
	height:20px;
	font-size: 13px;
	font-weight: bold;
	background-color: #990000;
	color: #CCFFFF;
	border-radius: 5px;
	text-align: center;
	transform: translateX(-50%);
	display: block;
}

.cm-menu-combo {
	cursor: pointer;
	width: 310px;
	box-sizing: border-box;
}

.cm-small-button {
	width: 120px;
	height: 30px;
	position: relative;
	overflow: hidden;
	box-sizing: border-box;
	font-size: 17px !important;
}

#cm-install-customnodes-button {
	width: 200px;
	height: 30px;
	position: relative;
	overflow: hidden;
	box-sizing: border-box;
	font-size: 17px !important;
}

.cm-search-filter {
	width: 200px;
	height: 30px !important;
	position: relative;
	overflow: hidden;
	box-sizing: border-box;
}

.cb-node-label {
	width: 400px;
	height:28px;
	color: black;
	background-color: #777777;
	font-size: 18px;
	text-align: center;
	font-weight: bold;
}

#cm-close-button {
	width: calc(100% - 65px);
	bottom: 10px;
	position: absolute;
	overflow: hidden;
}

#cm-save-button {
	width: calc(100% - 65px);
	bottom:40px;
	position: absolute;
	overflow: hidden;
}
#cm-save-button:disabled {
	background-color: #444444;
}

.pysssss-workflow-arrow-2 {
	position: absolute;
	top: 0;
	bottom: 0;
	right: 0;
	font-size: 12px;
	display: flex;
	align-items: center;
	width: 24px;
	justify-content: center;
	background: rgba(255,255,255,0.1);
	content: "▼";
}
.pysssss-workflow-arrow-2:after {
	content: "▼";
 }
 .pysssss-workflow-arrow-2:hover {
	filter: brightness(1.6);
	background-color: var(--comfy-menu-bg);
 }
.pysssss-workflow-popup-2 ~ .litecontextmenu {
	transform: scale(1.3);
}
#workflowgallery-button-menu {
	z-index: 10000000000 !important;
}
#cm-manual-button-menu {
	z-index: 10000000000 !important;
}
`;

async function fetchNicknames() {
	const response1 = await api.fetchApi(`/customnode/getmappings?mode=nickname`);
	const mappings = await response1.json();

	let result = {};
	let nickname_patterns = [];

	for (let i in mappings) {
		let item = mappings[i];
		var nickname;
		if (item[1].nickname) {
			nickname = item[1].nickname;
		}
		else if (item[1].title) {
			nickname = item[1].title;
		}
		else {
			nickname = item[1].title_aux;
		}

		for (let j in item[0]) {
			result[item[0][j]] = nickname;
		}

		if(item[1].nodename_pattern) {
			nickname_patterns.push([item[1].nodename_pattern, nickname]);
		}
	}

	return [result, nickname_patterns];
}

const [nicknames, nickname_patterns] = await fetchNicknames();

function getNickname(node, nodename) {
	if(node.nickname) {
		return node.nickname;
	}
	else {
		if (nicknames[nodename]) {
			node.nickname = nicknames[nodename];
		}
		else if(node.getInnerNodes) {
			let pure_name = getPureName(node);
			let groupNode = app.graph.extra?.groupNodes?.[pure_name];
			if(groupNode) {
				let packname = groupNode.packname;
				node.nickname = packname;
			}
			return node.nickname;
		}
		else {
			for(let i in nickname_patterns) {
				let item = nickname_patterns[i];
				if(nodename.match(item[0])) {
					node.nickname = item[1];
				}
			}
		}

		return node.nickname;
	}
}

async function updateComfyUI() {
	let prev_text = update_comfyui_button.innerText;
	update_comfyui_button.innerText = "Updating ComfyUI...";
	update_comfyui_button.disabled = true;
	update_comfyui_button.style.backgroundColor = "gray";

	try {
		const response = await api.fetchApi('/comfyui_manager/update_comfyui');

		if (response.status == 400) {
			show_message('Failed to update ComfyUI.');
			return false;
		}

		if (response.status == 201) {
			show_message('ComfyUI has been successfully updated.');
		}
		else {
			show_message('ComfyUI is already up to date with the latest version.');
		}

		return true;
	}
	catch (exception) {
		show_message(`Failed to update ComfyUI / ${exception}`);
		return false;
	}
	finally {
		update_comfyui_button.disabled = false;
		update_comfyui_button.innerText = prev_text;
		update_comfyui_button.style.backgroundColor = "";
	}
}

function showVersionSelectorDialog(versions, current, onSelect) {
		const dialog = new ComfyDialog();
		dialog.element.style.zIndex = 100003;
		dialog.element.style.width = "300px";
		dialog.element.style.padding = "0";
		dialog.element.style.backgroundColor = "#2a2a2a";
		dialog.element.style.border = "1px solid #3a3a3a";
		dialog.element.style.borderRadius = "8px";
		dialog.element.style.boxSizing = "border-box";
		dialog.element.style.overflow = "hidden";

		const contentStyle = {
			width: "300px",
			display: "flex",
			flexDirection: "column",
			alignItems: "center",
			padding: "20px",
			boxSizing: "border-box",
			gap: "15px"
		};

		let selectedVersion = versions[0];

		const versionList = $el("select", {
			multiple: true,
			size: Math.min(10, versions.length),
			style: {
				width: "260px",
				height: "auto",
				backgroundColor: "#383838",
				color: "#ffffff",
				border: "1px solid #4a4a4a",
				borderRadius: "4px",
				padding: "5px",
				boxSizing: "border-box"
			}
		},
		versions.map((v, index) => $el("option", {
			value: v,
			textContent: v,
			selected: v === current
		}))
		);

		versionList.addEventListener('change', (e) => {
			selectedVersion = e.target.value;
			Array.from(e.target.options).forEach(opt => {
				opt.selected = opt.value === selectedVersion;
			});
		});

		const content = $el("div", {
			style: contentStyle
		}, [
			$el("h3", {
				textContent: "Select Version",
				style: {
					color: "#ffffff",
					backgroundColor: "#1a1a1a",
					padding: "10px 15px",
					margin: "0 0 10px 0",
					width: "260px",
					textAlign: "center",
					borderRadius: "4px",
					boxSizing: "border-box",
					whiteSpace: "nowrap",
					overflow: "hidden",
					textOverflow: "ellipsis"
				}
			}),
			versionList,
			$el("div", {
				style: {
					display: "flex",
					justifyContent: "space-between",
					width: "260px",
					gap: "10px"
				}
			}, [
				$el("button", {
					textContent: "Cancel",
					onclick: () => dialog.close(),
					style: {
						flex: "1",
						padding: "8px",
						backgroundColor: "#4a4a4a",
						color: "#ffffff",
						border: "none",
						borderRadius: "4px",
						cursor: "pointer",
						whiteSpace: "nowrap",
						overflow: "hidden",
						textOverflow: "ellipsis"
					}
				}),
				$el("button", {
					textContent: "Select",
					onclick: () => {
						if (selectedVersion) {
							onSelect(selectedVersion);
							dialog.close();
						} else {
							alert("Please select a version.");
						}
					},
					style: {
						flex: "1",
						padding: "8px",
						backgroundColor: "#4CAF50",
						color: "#ffffff",
						border: "none",
						borderRadius: "4px",
						cursor: "pointer",
						whiteSpace: "nowrap",
						overflow: "hidden",
						textOverflow: "ellipsis"
					}
				}),
			])
		]);

		dialog.show(content);
}

async function switchComfyUI() {
    let res = await api.fetchApi(`/comfyui_manager/comfyui_versions`, { cache: "no-store" });

    if(res.status == 200) {
        let obj = await res.json();

        let versions = [];
        let default_version;

        for(let v of obj.versions) {
            default_version = v;
            versions.push(v);
        }

        showVersionSelectorDialog(versions, obj.current, (selected_version) => {
            api.fetchApi(`/comfyui_manager/comfyui_switch_version?ver=${selected_version}`, { cache: "no-store" });
        });
    }
    else {
        show_message('Failed to fetch ComfyUI versions.');
    }
}


async function fetchUpdates(update_check_checkbox) {
	let prev_text = fetch_updates_button.innerText;
	fetch_updates_button.innerText = "Fetching updates...";
	fetch_updates_button.disabled = true;
	fetch_updates_button.style.backgroundColor = "gray";

	try {
		var mode = manager_instance.datasrc_combo.value;

		const response = await api.fetchApi(`/customnode/fetch_updates?mode=${mode}`);

		if (response.status != 200 && response.status != 201) {
			show_message('Failed to fetch updates.');
			return false;
		}

		if (response.status == 201) {
			show_message("There is an updated extension available.<BR><BR><P><B>NOTE:<BR>Fetch Updates is not an update.<BR>Please update from <button id='cm-install-customnodes-button'>Install Custom Nodes</button> </B></P>");

			const button = document.getElementById('cm-install-customnodes-button');
			button.addEventListener("click",
				async function() {
					app.ui.dialog.close();

					if(!CustomNodesManager.instance) {
						CustomNodesManager.instance = new CustomNodesManager(app, self);
					}
					await CustomNodesManager.instance.show(CustomNodesManager.ShowMode.UPDATE);
				}
			);

			update_check_checkbox.checked = false;
		}
		else {
			show_message('All extensions are already up-to-date with the latest versions.');
		}

		return true;
	}
	catch (exception) {
		show_message(`Failed to update custom nodes / ${exception}`);
		return false;
	}
	finally {
		fetch_updates_button.disabled = false;
		fetch_updates_button.innerText = prev_text;
		fetch_updates_button.style.backgroundColor = "";
	}
}

async function updateAll(update_check_checkbox, manager_dialog) {
	let prev_text = update_all_button.innerText;
	update_all_button.innerText = "Updating all custom nodes...";
	update_all_button.disabled = true;
	update_all_button.style.backgroundColor = "gray";

	try {
		var mode = manager_instance.datasrc_combo.value;

		update_all_button.innerText = "Updating all custom nodes...";
		const response = await api.fetchApi(`/customnode/update_all?mode=${mode}`);

		if (response.status == 403) {
			show_message('This action is not allowed with this security level configuration.');
			return false;
		}

		if (response.status == 400) {
			show_message('Failed to update ComfyUI or several extensions.<BR><BR>See terminal log.<BR>');
			return false;
		}

		if(response.status == 201) {
			const update_info = await response2.json();

			let failed_list = "";
			if(update_info.failed.length > 0) {
				failed_list = "<BR>FAILED: "+update_info.failed.join(", ");
			}

			let updated_list = "";
			if(update_info.updated.length > 0) {
				updated_list = "<BR>UPDATED: "+update_info.updated.join(", ");
			}

			show_message(
				"All extensions have been updated to the latest version.<BR>To apply the updated custom node, please <button class='cm-small-button' id='cm-reboot-button5'>RESTART</button> ComfyUI. And refresh browser.<BR>"
				+failed_list
				+updated_list
				);

			const rebootButton = document.getElementById('cm-reboot-button5');
			rebootButton.addEventListener("click",
				function() {
					if(rebootAPI()) {
						manager_dialog.close();
					}
				});
		}
		else {
			show_message('All extensions are already up-to-date with the latest versions.');
		}

		return true;
	}
	catch (exception) {
		show_message(`Failed to update ComfyUI or several extensions / ${exception}`);
		return false;
	}
	finally {
		update_all_button.disabled = false;
		update_all_button.innerText = prev_text;
		update_all_button.style.backgroundColor = "";
	}
}

function newDOMTokenList(initialTokens) {
	const tmp = document.createElement(`div`);

	const classList = tmp.classList;
	if (initialTokens) {
		initialTokens.forEach(token => {
		classList.add(token);
		});
	}

	return classList;
	}

// -----------
class ManagerMenuDialog extends ComfyDialog {
	createControlsMid() {
		let self = this;

		const res =
			[
				$el("button.cm-button", {
					type: "button",
					textContent: "Favorites Node List",
					onclick:
						() => {
							if(!CustomNodesManager.instance) {
								CustomNodesManager.instance = new CustomNodesManager(app, self);
							}
							CustomNodesManager.instance.show(CustomNodesManager.ShowMode.FAVORITES);
						}
				}),

				$el("button.cm-button", {
					type: "button",
					textContent: "Full Node List",
					onclick:
						() => {
							if(!CustomNodesManager.instance) {
								CustomNodesManager.instance = new CustomNodesManager(app, self);
							}
							CustomNodesManager.instance.show(CustomNodesManager.ShowMode.NORMAL);
						}
				}),

				$el("button.cm-button", {
					type: "button",
					textContent: "Missing Node List",
					onclick:
						() => {
							if(!CustomNodesManager.instance) {
								CustomNodesManager.instance = new CustomNodesManager(app, self);
							}
							CustomNodesManager.instance.show(CustomNodesManager.ShowMode.MISSING);
						}
				}),

				$el("br", {}, []),

				$el("button.cm-button", {
					type: "button",
					textContent: "Model Manager",
					onclick:
						() => {
							if(!ModelManager.instance) {
								ModelManager.instance = new ModelManager(app, self);
							}
							ModelManager.instance.show();
						}
				}),

				$el("br", {}, []),

				$el("button.cm-button-red", {
					type: "button",
					textContent: "Restart",
					onclick: () => rebootAPI()
				}),
			];

		let migration_btn =
			$el("button.cm-button-orange", {
				type: "button",
				textContent: "Migrate to New Node System",
				onclick: () => migrateAPI()
			});

		migration_btn.style.display = 'none';

		res.push(migration_btn);

		api.fetchApi('/manager/need_to_migrate')
			.then(response => response.text())
			.then(text => {
				if (text === 'True') {
					migration_btn.style.display = 'block';
				}
			})
			.catch(error => {
				console.error('Error checking migration status:', error);
			});

		return res;
	}

	createControlsLeft() {
		let self = this;

		this.update_check_checkbox = $el("input",{type:'checkbox', id:"skip_update_check"},[])
		const uc_checkbox_text = $el("label",{for:"skip_update_check"},[" Skip update check"])
		uc_checkbox_text.style.color = "var(--fg-color)";
		uc_checkbox_text.style.cursor = "pointer";
		this.update_check_checkbox.checked = true;

		// db mode
		this.datasrc_combo = document.createElement("select");
		this.datasrc_combo.setAttribute("title", "Configure where to retrieve node/model information. If set to 'local,' the channel is ignored, and if set to 'channel (remote),' it fetches the latest information each time the list is opened.");
		this.datasrc_combo.className = "cm-menu-combo";
		this.datasrc_combo.appendChild($el('option', { value: 'cache', text: 'DB: Channel (1day cache)' }, []));
		this.datasrc_combo.appendChild($el('option', { value: 'local', text: 'DB: Local' }, []));
		this.datasrc_combo.appendChild($el('option', { value: 'url', text: 'DB: Channel (remote)' }, []));

		// channel
		let channel_combo = document.createElement("select");
		channel_combo.setAttribute("title", "Configure the channel for retrieving data from the Custom Node list (including missing nodes) or the Model list.");
		channel_combo.className = "cm-menu-combo";
		api.fetchApi('/manager/channel_url_list')
			.then(response => response.json())
			.then(async data => {
				try {
					let urls = data.list;
					for (let i in urls) {
						if (urls[i] != '') {
							let name_url = urls[i].split('::');
							channel_combo.appendChild($el('option', { value: name_url[0], text: `Channel: ${name_url[0]}` }, []));
						}
					}

					channel_combo.addEventListener('change', function (event) {
						api.fetchApi(`/manager/channel_url_list?value=${event.target.value}`);
					});

					channel_combo.value = data.selected;
				}
				catch (exception) {

				}
			});


		return [
			$el("div", {}, [this.update_check_checkbox, uc_checkbox_text]),
			$el("br", {}, []),
			this.datasrc_combo,
			channel_combo,
			$el("br", {}, []),

            $el("button.cm-button", {
                type: "button",
                textContent: "Snapshot Manager",
                onclick:
                    () => {
                        if(!SnapshotManager.instance)
                        SnapshotManager.instance = new SnapshotManager(app, self);
                        SnapshotManager.instance.show();
                    }
            })
		];
	}

	createControlsRight() {
		let self = this;

		fetch_updates_button =
			$el("button.cm-button", {
				type: "button",
				textContent: "Fetch Updates",
				onclick:
					() => fetchUpdates(this.update_check_checkbox)
			});

		update_all_button =
			$el("button.cm-button", {
				type: "button",
				textContent: "Update All Custom Nodes",
				onclick:
					() => updateAll(this.update_check_checkbox, self)
			});

		const res =
			[
				update_all_button,
                $el("br", {}, []),
				fetch_updates_button
			];

		return res;
	}

	constructor() {
		super();

		const close_button = $el("button", { id: "cm-close-button", type: "button", textContent: "Close", onclick: () => this.close() });

		const content =
				$el("div.comfy-modal-content",
					[
						$el("tr.cm-title", {}, [
								$el("font", {size:6, color:"white"}, [`ComfyUI Manager (Essential)`])]
							),
						$el("br", {}, []),
						$el("div.cm-menu-container",
							[
								$el("div.cm-menu-column", [...this.createControlsLeft()]),
								$el("div.cm-menu-column", [...this.createControlsMid()]),
								$el("div.cm-menu-column", [...this.createControlsRight()])
							]),

						$el("br", {}, []),
						close_button,
					]
				);

		content.style.width = '100%';
		content.style.height = '100%';

		this.element = $el("div.comfy-modal", { id:'cm-manager-dialog', parent: document.body }, [ content ]);
	}

	show() {
		this.element.style.display = "block";
	}
}


app.registerExtension({
	name: "Comfy.ManagerMenu",
	init() {
		$el("style", {
			textContent: style,
			parent: document.head,
		});
	},
	async setup() {
		const menu = document.querySelector(".comfy-menu");
		const separator = document.createElement("hr");

		separator.style.margin = "20px 0";
		separator.style.width = "100%";
		menu.append(separator);

        const resp = await api.fetchApi('/manager/show_menu');

        if(resp.status == 200) {
            // new style Manager buttons
            // unload models button into new style Manager button
            let cmGroup = new (await import("../../scripts/ui/components/buttonGroup.js")).ComfyButtonGroup(
                new(await import("../../scripts/ui/components/button.js")).ComfyButton({
                    icon: "star",
                    action: () => {
                        if(!manager_instance)
                            setManagerInstance(new ManagerMenuDialog());

                        if(!CustomNodesManager.instance) {
                            CustomNodesManager.instance = new CustomNodesManager(app, self);
                        }
                        CustomNodesManager.instance.show(CustomNodesManager.ShowMode.FAVORITES);
                    },
                    tooltip: "Show favorite custom node list",
                    content: "Manager",
                    classList: "comfyui-button comfyui-menu-mobile-collapse primary"
                }).element,
                new(await import("../../scripts/ui/components/button.js")).ComfyButton({
                    icon: "puzzle",
                    action: () => {
                        if(!manager_instance)
                            setManagerInstance(new ManagerMenuDialog());
                        manager_instance.show();
                    },
                    tooltip: "ComfyUI Manager",
                }).element
            );

            app.menu?.settingsGroup.element.before(cmGroup.element);

            // old style Manager button
            const managerButton = document.createElement("button");
            managerButton.textContent = "Manager";
            managerButton.onclick = () => {
                    if(!manager_instance)
                        setManagerInstance(new ManagerMenuDialog());
                    manager_instance.show();
                }
            menu.append(managerButton);
		}
	}
});
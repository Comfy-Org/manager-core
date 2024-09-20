import { api } from "../../scripts/api.js";
import { app } from "../../scripts/app.js";
import { sleep } from "./common.js";

async function tryInstallCustomNode(event) {
	console.log('Starting tryInstallCustomNode function');

	let msg = '-= [ComfyUI Manager] extension installation request =-\n\n';
	msg += `The '${event.detail.sender}' extension requires the installation of the '${event.detail.target.title}' extension. `;

	console.log('Checking installation status');
	if(event.detail.target.installed == 'Disabled') {
		console.log('Extension is disabled');
		msg += 'However, the extension is currently disabled. Would you like to enable it and reboot?'
	}
	else if(event.detail.target.installed == 'True') {
		console.log('Extension is installed but in import-fail state or incompatible');
		msg += 'However, it seems that the extension is in an import-fail state or is not compatible with the current version. Please address this issue.';
	}
	else {
		console.log('Extension is not installed');
		msg += `Would you like to install it and reboot?`;
	}

	msg += `\n\nRequest message:\n${event.detail.msg}`;

	console.log('Checking if extension is already installed');
	if(event.detail.target.installed == 'True') {
		console.log('Extension is already installed, showing alert');
		alert(msg);
		return;
	}

	console.log('Prompting user for confirmation');
	let res = confirm(msg);
	if(res) {
		console.log('User confirmed, proceeding with action');
		if(event.detail.target.installed == 'Disabled') {
			console.log('Toggling active state for disabled extension');
			const response = await api.fetchApi(`/customnode/toggle_active`, {
										method: 'POST',
										headers: { 'Content-Type': 'application/json' },
										body: JSON.stringify(event.detail.target)
									});
		}
		else {
			console.log('Installing new extension');
			await sleep(300);
			app.ui.dialog.show(`Installing... '${event.detail.target.title}'`);

			const response = await api.fetchApi(`/customnode/install`, {
										method: 'POST',
										headers: { 'Content-Type': 'application/json' },
										body: JSON.stringify({ ...event.detail.target, noDeps: true })
									});

			if(response.status == 403) {
				show_message('This action is not allowed with this security level configuration.');
				return false;
			}
		}

		console.log('Initiating reboot');
		let response = await api.fetchApi("/manager/reboot");
		if(response.status == 403) {
			show_message('This action is not allowed with this security level configuration.');
			return false;
		}

		await sleep(300);

		console.log('Showing reboot dialog');
		app.ui.dialog.show(`Rebooting...`);
	}
}

api.addEventListener("cm-api-try-install-customnode", tryInstallCustomNode);

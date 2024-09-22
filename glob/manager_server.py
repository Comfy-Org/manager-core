import traceback

import folder_paths
import locale
import subprocess  # don't remove this
import concurrent
import nodes
import os
import sys
import threading
import re
import shutil
import git

from server import PromptServer
import manager_core as core
import manager_util
import cm_global

print(f"### Loading: manager-core ({core.version_str})")

comfy_ui_hash = "-"
comfyui_tag = None

SECURITY_MESSAGE_MIDDLE_OR_BELOW = f"ERROR: To use this action, a security_level of `middle or below` is required. Please contact the administrator.\nReference: https://github.com/ltdrdata/ComfyUI-Manager#security-policy"
SECURITY_MESSAGE_NORMAL_MINUS = f"ERROR: To use this feature, you must either set '--listen' to a local IP and set the security level to 'normal-' or lower, or set the security level to 'middle' or 'weak'. Please contact the administrator.\nReference: https://github.com/ltdrdata/ComfyUI-Manager#security-policy"
SECURITY_MESSAGE_GENERAL = f"ERROR: This installation is not allowed in this security_level. Please contact the administrator.\nReference: https://github.com/ltdrdata/ComfyUI-Manager#security-policy"

routes = PromptServer.instance.routes


def handle_stream(stream, prefix):
    stream.reconfigure(encoding=locale.getpreferredencoding(), errors='replace')
    for msg in stream:
        if prefix == '[!]' and ('it/s]' in msg or 's/it]' in msg) and ('%|' in msg or 'it [' in msg):
            if msg.startswith('100%'):
                print('\r' + msg, end="", file=sys.stderr),
            else:
                print('\r' + msg[:-1], end="", file=sys.stderr),
        else:
            if prefix == '[!]':
                print(prefix, msg, end="", file=sys.stderr)
            else:
                print(prefix, msg, end="")


from comfy.cli_args import args


is_local_mode = args.listen.startswith('127.') or args.listen.startswith('local.')


def is_allowed_security_level(level):
    if level == 'high':
        if is_local_mode:
            return core.get_config()['security_level'].lower() in ['weak', 'normal-']
        else:
            return core.get_config()['security_level'].lower() == 'weak'
    elif level == 'middle':
        return core.get_config()['security_level'].lower() in ['weak', 'normal', 'normal-']
    else:
        return True


async def get_risky_level(files):
    json_data1 = await core.get_data_by_mode('local', 'custom-node-list.json')
    json_data2 = await core.get_data_by_mode('cache', 'custom-node-list.json', channel_url='https://github.com/ltdrdata/ComfyUI-Manager/raw/main')

    all_urls = set()
    for x in json_data1['custom_nodes'] + json_data2['custom_nodes']:
        all_urls.update(x['files'])

    for x in files:
        if x not in all_urls:
            return "high"

    return "middle"


class ManagerFuncsInComfyUI(core.ManagerFuncs):
    def run_script(self, cmd, cwd='.'):
        if len(cmd) > 0 and cmd[0].startswith("#"):
            print(f"[ComfyUI-Manager] Unexpected behavior: `{cmd}`")
            return 0

        process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

        stdout_thread = threading.Thread(target=handle_stream, args=(process.stdout, ""))
        stderr_thread = threading.Thread(target=handle_stream, args=(process.stderr, "[!]"))

        stdout_thread.start()
        stderr_thread.start()

        stdout_thread.join()
        stderr_thread.join()

        return process.wait()


core.manager_funcs = ManagerFuncsInComfyUI()

sys.path.append('../..')

from manager_downloader import download_url

core.comfy_path = os.path.dirname(folder_paths.__file__)
core.js_path = os.path.join(core.comfy_path, "web", "extensions")

local_db_custom_node_list = os.path.join(core.comfyui_manager_path, "custom-node-list.json")
local_db_extension_node_mappings = os.path.join(core.comfyui_manager_path, "extension-node-map.json")


def set_badge_mode(mode):
    core.get_config()['badge_mode'] = mode


def print_comfyui_version():
    global comfy_ui_hash
    global comfyui_tag

    is_detached = False
    try:
        repo = git.Repo(os.path.dirname(folder_paths.__file__))
        core.comfy_ui_revision = len(list(repo.iter_commits('HEAD')))

        comfy_ui_hash = repo.head.commit.hexsha
        cm_global.variables['comfyui.revision'] = core.comfy_ui_revision

        core.comfy_ui_commit_datetime = repo.head.commit.committed_datetime
        cm_global.variables['comfyui.commit_datetime'] = core.comfy_ui_commit_datetime

        is_detached = repo.head.is_detached
        current_branch = repo.active_branch.name

        if current_branch == "master":
            comfyui_tag = repo.git.describe('--tags', repo.heads.main.commit.hexsha)
            if not comfyui_tag.startswith("v"):
                comfyui_tag = None

        try:
            if core.comfy_ui_commit_datetime.date() < core.comfy_ui_required_commit_datetime.date():
                print(f"\n\n## [WARN] ComfyUI-Manager: Your ComfyUI version ({core.comfy_ui_revision})[{core.comfy_ui_commit_datetime.date()}] is too old. Please update to the latest version. ##\n\n")
        except:
            pass

        # process on_revision_detected -->
        if 'cm.on_revision_detected_handler' in cm_global.variables:
            for k, f in cm_global.variables['cm.on_revision_detected_handler']:
                try:
                    f(core.comfy_ui_revision)
                except Exception:
                    print(f"[ERROR] '{k}' on_revision_detected_handler")
                    traceback.print_exc()

            del cm_global.variables['cm.on_revision_detected_handler']
        else:
            print(f"[ComfyUI-Manager] Some features are restricted due to your ComfyUI being outdated.")
        # <--

        if current_branch == "master":
            if comfyui_tag:
                print(f"### ComfyUI Version: {comfyui_tag} | Released on '{core.comfy_ui_commit_datetime.date()}'")
            else:
                print(f"### ComfyUI Revision: {core.comfy_ui_revision} [{comfy_ui_hash[:8]}] | Released on '{core.comfy_ui_commit_datetime.date()}'")
        else:
            print(f"### ComfyUI Revision: {core.comfy_ui_revision} on '{current_branch}' [{comfy_ui_hash[:8]}] | Released on '{core.comfy_ui_commit_datetime.date()}'")
    except:
        if is_detached:
            print(f"### ComfyUI Revision: {core.comfy_ui_revision} [{comfy_ui_hash[:8]}] *DETACHED | Released on '{core.comfy_ui_commit_datetime.date()}'")
        else:
            print("### ComfyUI Revision: UNKNOWN (The currently installed ComfyUI is not a Git repository)")


print_comfyui_version()
core.check_invalid_nodes()


def setup_environment():
    git_exe = core.get_config()['git_exe']

    if git_exe != '':
        git.Git().update_environment(GIT_PYTHON_GIT_EXECUTABLE=git_exe)


setup_environment()

# Expand Server api

import server
from aiohttp import web
import aiohttp
import json
import zipfile
import urllib.request


def check_state_of_git_node_pack(node_packs, do_fetch=False, do_update_check=True, do_update=False):
    if do_fetch:
        print("Start fetching...", end="")
    elif do_update:
        print("Start updating...", end="")
    elif do_update_check:
        print("Start update check...", end="")

    def process_custom_node(item):
        core.check_state_of_git_node_pack_single(item, do_fetch, do_update_check, do_update)

    with concurrent.futures.ThreadPoolExecutor(4) as executor:
        for k, v in node_packs.items():
            if v.get('active_version') in ['unknown', 'nightly']:
                executor.submit(process_custom_node, v)

    if do_fetch:
        print(f"\x1b[2K\rFetching done.")
    elif do_update:
        update_exists = any(item.get('updatable', False) for item in node_packs.values())
        if update_exists:
            print(f"\x1b[2K\rUpdate done.")
        else:
            print(f"\x1b[2K\rAll extensions are already up-to-date.")
    elif do_update_check:
        print(f"\x1b[2K\rUpdate check done.")


def nickname_filter(json_obj):
    preemptions_map = {}

    for k, x in json_obj.items():
        if 'preemptions' in x[1]:
            for y in x[1]['preemptions']:
                preemptions_map[y] = k
        elif k.endswith("/ComfyUI"):
            for y in x[0]:
                preemptions_map[y] = k

    updates = {}
    for k, x in json_obj.items():
        removes = set()
        for y in x[0]:
            k2 = preemptions_map.get(y)
            if k2 is not None and k != k2:
                removes.add(y)

        if len(removes) > 0:
            updates[k] = [y for y in x[0] if y not in removes]

    for k, v in updates.items():
        json_obj[k][0] = v

    return json_obj


@routes.get("/customnode/getmappings")
async def fetch_customnode_mappings(request):
    """
    provide unified (node -> node pack) mapping list
    """
    mode = request.rel_url.query["mode"]

    nickname_mode = False
    if mode == "nickname":
        mode = "local"
        nickname_mode = True

    json_obj = await core.get_data_by_mode(mode, 'extension-node-map.json')
    json_obj = core.map_to_unified_keys(json_obj)

    if nickname_mode:
        json_obj = nickname_filter(json_obj)

    all_nodes = set()
    patterns = []
    for k, x in json_obj.items():
        all_nodes.update(set(x[0]))

        if 'nodename_pattern' in x[1]:
            patterns.append((x[1]['nodename_pattern'], x[0]))

    missing_nodes = set(nodes.NODE_CLASS_MAPPINGS.keys()) - all_nodes

    for x in missing_nodes:
        for pat, item in patterns:
            if re.match(pat, x):
                item.append(x)

    return web.json_response(json_obj, content_type='application/json')


@routes.get("/customnode/fetch_updates")
async def fetch_updates(request):
    try:
        if request.rel_url.query["mode"] == "local":
            channel = 'local'
        else:
            channel = core.get_config()['channel_url']

        await core.unified_manager.reload(request.rel_url.query["mode"])
        await core.unified_manager.get_custom_nodes(channel, request.rel_url.query["mode"])

        res = core.unified_manager.fetch_or_pull_git_repo(is_pull=False)

        for x in res['failed']:
            print(f"FETCH FAILED: {x}")

        print("\nDone.")

        if len(res['updated']) > 0:
            return web.Response(status=201)

        return web.Response(status=200)
    except:
        traceback.print_exc()
        return web.Response(status=400)


@routes.get("/customnode/update_all")
async def update_all(request):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)

    try:
        core.save_snapshot_with_postfix('autosave')

        if request.rel_url.query["mode"] == "local":
            channel = 'local'
        else:
            channel = core.get_config()['channel_url']

        await core.unified_manager.reload(request.rel_url.query["mode"])
        await core.unified_manager.get_custom_nodes(channel, request.rel_url.query["mode"])

        updated_cnr = []
        for k, v in core.unified_manager.active_nodes.items():
            if v[0] != 'nightly':
                res = core.unified_manager.unified_update(k, v[0])
                if res.action == 'switch-cnr' and res:
                    updated_cnr.append(k)

        res = core.unified_manager.fetch_or_pull_git_repo(is_pull=True)

        res['updated'] += updated_cnr

        for x in res['failed']:
            print(f"PULL FAILED: {x}")

        if len(res['updated']) == 0 and len(res['failed']) == 0:
            status = 200
        else:
            status = 201

        print(f"\nDone.")
        return web.json_response(res, status=status, content_type='application/json')
    except:
        traceback.print_exc()
        return web.Response(status=400)
    finally:
        core.clear_pip_cache()


def convert_markdown_to_html(input_text):
    pattern_a = re.compile(r'\[a/([^]]+)\]\(([^)]+)\)')
    pattern_w = re.compile(r'\[w/([^]]+)\]')
    pattern_i = re.compile(r'\[i/([^]]+)\]')
    pattern_bold = re.compile(r'\*\*([^*]+)\*\*')
    pattern_white = re.compile(r'%%([^*]+)%%')

    def replace_a(match):
        return f"<a href='{match.group(2)}' target='blank'>{match.group(1)}</a>"

    def replace_w(match):
        return f"<p class='cm-warn-note'>{match.group(1)}</p>"

    def replace_i(match):
        return f"<p class='cm-info-note'>{match.group(1)}</p>"

    def replace_bold(match):
        return f"<B>{match.group(1)}</B>"

    def replace_white(match):
        return f"<font color='white'>{match.group(1)}</font>"

    input_text = input_text.replace('\\[', '&#91;').replace('\\]', '&#93;').replace('<', '&lt;').replace('>', '&gt;')

    result_text = re.sub(pattern_a, replace_a, input_text)
    result_text = re.sub(pattern_w, replace_w, result_text)
    result_text = re.sub(pattern_i, replace_i, result_text)
    result_text = re.sub(pattern_bold, replace_bold, result_text)
    result_text = re.sub(pattern_white, replace_white, result_text)

    return result_text.replace("\n", "<BR>")


def populate_markdown(x):
    if 'description' in x:
        x['description'] = convert_markdown_to_html(manager_util.sanitize_tag(x['description']))

    if 'name' in x:
        x['name'] = manager_util.sanitize_tag(x['name'])

    if 'title' in x:
        x['title'] = manager_util.sanitize_tag(x['title'])


@routes.get("/customnode/getlist")
async def fetch_customnode_list(request):
    """
    provide unified custom node list
    """
    if "skip_update" in request.rel_url.query and request.rel_url.query["skip_update"] == "true":
        skip_update = True
    else:
        skip_update = False

    if request.rel_url.query["mode"] == "local":
        channel = 'local'
    else:
        channel = core.get_config()['channel_url']

    node_packs = await core.get_unified_total_nodes(channel, request.rel_url.query["mode"])
    json_obj_github = core.get_data_by_mode(request.rel_url.query["mode"], 'github-stats.json', 'default')
    json_obj_extras = core.get_data_by_mode(request.rel_url.query["mode"], 'extras.json', 'default')

    core.populate_github_stats(node_packs, await json_obj_github)
    core.populate_favorites(node_packs, await json_obj_extras)

    check_state_of_git_node_pack(node_packs, False, do_update_check=not skip_update)

    for v in node_packs.values():
        populate_markdown(v)

    if channel != 'local':
        found = 'custom'

        for name, url in core.get_channel_dict().items():
            if url == channel:
                found = name
                break

        channel = found

    result = dict(channel=channel, node_packs=node_packs)

    return web.json_response(result, content_type='application/json')


@PromptServer.instance.routes.get("/snapshot/getlist")
async def get_snapshot_list(request):
    snapshots_directory = os.path.join(core.comfyui_manager_path, 'snapshots')
    items = [f[:-5] for f in os.listdir(snapshots_directory) if f.endswith('.json')]
    items.sort(reverse=True)
    return web.json_response({'items': items}, content_type='application/json')


@routes.get("/snapshot/remove")
async def remove_snapshot(request):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)
    
    try:
        target = request.rel_url.query["target"]

        path = os.path.join(core.comfyui_manager_path, 'snapshots', f"{target}.json")
        if os.path.exists(path):
            os.remove(path)

        return web.Response(status=200)
    except:
        return web.Response(status=400)


@routes.get("/snapshot/restore")
async def remove_snapshot(request):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)
    
    try:
        target = request.rel_url.query["target"]

        path = os.path.join(core.comfyui_manager_path, 'snapshots', f"{target}.json")
        if os.path.exists(path):
            if not os.path.exists(core.startup_script_path):
                os.makedirs(core.startup_script_path)

            target_path = os.path.join(core.startup_script_path, "restore-snapshot.json")
            shutil.copy(path, target_path)

            print(f"Snapshot restore scheduled: `{target}`")
            return web.Response(status=200)

        print(f"Snapshot file not found: `{path}`")
        return web.Response(status=400)
    except:
        return web.Response(status=400)


@routes.get("/snapshot/get_current")
async def get_current_snapshot_api(request):
    try:
        return web.json_response(core.get_current_snapshot(), content_type='application/json')
    except:
        return web.Response(status=400)


@routes.get("/snapshot/save")
async def save_snapshot(request):
    try:
        core.save_snapshot_with_postfix('snapshot')
        return web.Response(status=200)
    except:
        return web.Response(status=400)


def unzip_install(files):
    temp_filename = 'manager-temp.zip'
    for url in files:
        if url.endswith("/"):
            url = url[:-1]
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

            req = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(req)
            data = response.read()

            with open(temp_filename, 'wb') as f:
                f.write(data)

            with zipfile.ZipFile(temp_filename, 'r') as zip_ref:
                zip_ref.extractall(core.get_default_custom_nodes_path())

            os.remove(temp_filename)
        except Exception as e:
            print(f"Install(unzip) error: {url} / {e}", file=sys.stderr)
            return False

    print("Installation was successful.")
    return True


def download_url_with_agent(url, save_path):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

        req = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(req)
        data = response.read()

        if not os.path.exists(os.path.dirname(save_path)):
            os.makedirs(os.path.dirname(save_path))

        with open(save_path, 'wb') as f:
            f.write(data)

    except Exception as e:
        print(f"Download error: {url} / {e}", file=sys.stderr)
        return False

    print("Installation was successful.")
    return True


def copy_install(files, js_path_name=None):
    for url in files:
        if url.endswith("/"):
            url = url[:-1]
        try:
            filename = os.path.basename(url)
            if url.endswith(".py"):
                download_url(url, core.get_default_custom_nodes_path(), filename)
            else:
                path = os.path.join(core.js_path, js_path_name) if js_path_name is not None else core.js_path
                if not os.path.exists(path):
                    os.makedirs(path)
                download_url(url, path, filename)

        except Exception as e:
            print(f"Install(copy) error: {url} / {e}", file=sys.stderr)
            return False

    print("Installation was successful.")
    return True


def copy_uninstall(files, js_path_name='.'):
    for url in files:
        if url.endswith("/"):
            url = url[:-1]
        dir_name = os.path.basename(url)
        base_path = core.get_default_custom_nodes_path() if url.endswith('.py') else os.path.join(core.js_path, js_path_name)
        file_path = os.path.join(base_path, dir_name)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            elif os.path.exists(file_path + ".disabled"):
                os.remove(file_path + ".disabled")
        except Exception as e:
            print(f"Uninstall(copy) error: {url} / {e}", file=sys.stderr)
            return False

    print("Uninstallation was successful.")
    return True


def copy_set_active(files, is_disable, js_path_name='.'):
    if is_disable:
        action_name = "Disable"
    else:
        action_name = "Enable"

    for url in files:
        if url.endswith("/"):
            url = url[:-1]
        dir_name = os.path.basename(url)
        base_path = core.get_default_custom_nodes_path() if url.endswith('.py') else os.path.join(core.js_path, js_path_name)
        file_path = os.path.join(base_path, dir_name)

        try:
            if is_disable:
                current_name = file_path
                new_name = file_path + ".disabled"
            else:
                current_name = file_path + ".disabled"
                new_name = file_path

            os.rename(current_name, new_name)

        except Exception as e:
            print(f"{action_name}(copy) error: {url} / {e}", file=sys.stderr)

            return False

    print(f"{action_name} was successful.")
    return True


@routes.get("/customnode/versions/{node_name}")
async def get_cnr_versions(request):
    node_name = request.match_info.get("node_name", None)
    versions = core.cnr_utils.all_versions_of_node(node_name)

    if versions:
        return web.json_response(versions, content_type='application/json')

    return web.Response(status=400)


@routes.get("/customnode/disabled_versions/{node_name}")
async def get_disabled_versions(request):
    node_name = request.match_info.get("node_name", None)
    versions = []
    if node_name in core.unified_manager.nightly_inactive_nodes:
        versions.append(dict(version='nightly'))

    for v in core.unified_manager.cnr_inactive_nodes.get(node_name, {}).keys():
        versions.append(dict(version=v))

    if versions:
        return web.json_response(versions, content_type='application/json')

    return web.Response(status=400)


@routes.post("/customnode/reinstall")
async def reinstall_custom_node(request):
    await uninstall_custom_node(request)
    await install_custom_node(request)


@routes.post("/customnode/install")
async def install_custom_node(request):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)

    json_data = await request.json()

    # non-nightly cnr is safe
    risky_level = None
    cnr_id = json_data.get('id')
    skip_post_install = json_data.get('skip_post_install')

    if json_data['version'] != 'unknown':
        selected_version = json_data.get('selected_version', 'latest')
        if selected_version != 'nightly':
            risky_level = 'low'
            node_spec_str = f"{cnr_id}@{selected_version}"
        else:
            node_spec_str = f"{cnr_id}@nightly"
    else:
        # unknown
        unknown_name = os.path.basename(json_data['files'][0])
        node_spec_str = f"{unknown_name}@unknown"

    # apply security policy if not cnr node (nightly isn't regarded as cnr node)
    if risky_level is None:
        risky_level = await get_risky_level(json_data['files'])

    if not is_allowed_security_level(risky_level):
        print(SECURITY_MESSAGE_GENERAL)
        return web.Response(status=404)

    node_spec = core.unified_manager.resolve_node_spec(node_spec_str)

    if node_spec is None:
        return

    node_name, version_spec, is_specified = node_spec
    res = await core.unified_manager.install_by_id(node_name, version_spec, json_data['channel'], json_data['mode'], return_postinstall=skip_post_install)
    # discard post install if skip_post_install mode

    if res not in ['skip', 'enable', 'install-git', 'install-cnr', 'switch-cnr']:
        return web.Response(status=400)

    return web.Response(status=200)


@routes.post("/customnode/fix")
async def fix_custom_node(request):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)

    json_data = await request.json()

    node_id = json_data.get('id')
    node_ver = json_data['version']
    if node_ver != 'unknown':
        node_name = node_id
    else:
        # unknown
        node_name = os.path.basename(json_data['files'][0])

    res = core.unified_manager.unified_fix(node_name, node_ver)

    if res.result:
        print(f"After restarting ComfyUI, please refresh the browser.")
        return web.json_response({}, content_type='application/json')

    print(f"ERROR: An error occurred while fixing '{node_name}@{node_ver}'.")
    return web.Response(status=400)


@routes.post("/customnode/uninstall")
async def uninstall_custom_node(request):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)

    json_data = await request.json()

    node_id = json_data.get('id')
    if json_data['version'] != 'unknown':
        is_unknown = False
        node_name = node_id
    else:
        # unknown
        is_unknown = True
        node_name = os.path.basename(json_data['files'][0])

    res = core.unified_manager.unified_uninstall(node_name, is_unknown)

    if res.result:
        print(f"After restarting ComfyUI, please refresh the browser.")
        return web.json_response({}, content_type='application/json')

    print(f"ERROR: An error occurred while uninstalling '{node_name}'.")
    return web.Response(status=400)


@routes.post("/customnode/update")
async def update_custom_node(request):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)

    json_data = await request.json()

    node_id = json_data.get('id')
    if json_data['version'] != 'unknown':
        node_name = node_id
    else:
        # unknown
        node_name = os.path.basename(json_data['files'][0])

    res = core.unified_manager.unified_update(node_name, json_data['version'])

    core.clear_pip_cache()

    if res.result:
        print(f"After restarting ComfyUI, please refresh the browser.")
        return web.json_response({}, content_type='application/json')

    print(f"ERROR: An error occurred while updating '{node_name}'.")
    return web.Response(status=400)


@routes.get("/comfyui_manager/comfyui_versions")
async def comfyui_versions(request):
    try:
        res, current = core.get_comfyui_versions()
        return web.json_response({'versions': res, 'current': current}, status=200, content_type='application/json')
    except Exception as e:
        print(f"ComfyUI update fail: {e}", file=sys.stderr)

    return web.Response(status=400)


@routes.post("/customnode/disable")
async def disable_node(request):
    json_data = await request.json()

    node_id = json_data.get('id')
    if json_data['version'] != 'unknown':
        is_unknown = False
        node_name = node_id
    else:
        # unknown
        is_unknown = True
        node_name = os.path.basename(json_data['files'][0])

    res = core.unified_manager.unified_disable(node_name, is_unknown)

    if res:
        return web.json_response({}, content_type='application/json')

    return web.Response(status=400)


@routes.get("/manager/migrate_unmanaged_nodes")
async def migrate_unmanaged_nodes(request):
    print(f"[ComfyUI-Manager] Migrating unmanaged nodes...")
    await core.unified_manager.migrate_unmanaged_nodes()
    print("Done.")
    return web.Response(status=200)


@routes.get("/manager/need_to_migrate")
async def need_to_migrate(request):
    return web.Response(text=str(core.need_to_migrate), status=200)


@routes.get("/manager/badge_mode")
async def badge_mode(request):
    if "value" in request.rel_url.query:
        set_badge_mode(request.rel_url.query['value'])
        core.write_config()
    else:
        return web.Response(text=core.get_config()['badge_mode'], status=200)

    return web.Response(status=200)


@routes.get("/manager/channel_url_list")
async def channel_url_list(request):
    channels = core.get_channel_dict()
    if "value" in request.rel_url.query:
        channel_url = channels.get(request.rel_url.query['value'])
        if channel_url is not None:
            core.get_config()['channel_url'] = channel_url
            core.write_config()
    else:
        selected = 'custom'
        selected_url = core.get_config()['channel_url']

        for name, url in channels.items():
            if url == selected_url:
                selected = name
                break

        res = {'selected': selected,
               'list': core.get_channel_list()}
        return web.json_response(res, status=200)

    return web.Response(status=200)


def add_target_blank(html_text):
    pattern = r'(<a\s+href="[^"]*"\s*[^>]*)(>)'

    def add_target(match):
        if 'target=' not in match.group(1):
            return match.group(1) + ' target="_blank"' + match.group(2)
        return match.group(0)

    modified_html = re.sub(pattern, add_target, html_text)

    return modified_html


@routes.get("/manager/reboot")
def restart(self):
    if not is_allowed_security_level('middle'):
        print(SECURITY_MESSAGE_MIDDLE_OR_BELOW)
        return web.Response(status=403)

    try:
        sys.stdout.close_log()
    except Exception as e:
        pass

    if '__COMFY_CLI_SESSION__' in os.environ:
        with open(os.path.join(os.environ['__COMFY_CLI_SESSION__'] + '.reboot'), 'w') as file:
            pass

        print(f"\nRestarting...\n\n")
        exit(0)

    print(f"\nRestarting... [Legacy Mode]\n\n")
    if sys.platform.startswith('win32'):
        return os.execv(sys.executable, ['"' + sys.executable + '"', '"' + sys.argv[0] + '"'] + sys.argv[1:])
    else:
        return os.execv(sys.executable, [sys.executable] + sys.argv)


@routes.get("/manager/show_menu")
def show_menu(self):
    if cm_global.variables['manager-core.show_menu']:
        return web.Response(status=200)
    else:
        return web.Response(status=201)


def sanitize_filename(input_string):
    result_string = re.sub(r'[^a-zA-Z0-9_]', '_', input_string)
    return result_string


args.enable_cors_header = "*"
if hasattr(PromptServer.instance, "app"):
    app = PromptServer.instance.app
    cors_middleware = server.create_cors_middleware(args.enable_cors_header)
    app.middlewares.append(cors_middleware)


def sanitize(data):
    return data.replace("<", "&lt;").replace(">", "&gt;")


async def _confirm_try_install(sender, custom_node_url, msg):
    json_obj = await core.get_data_by_mode('default', 'custom-node-list.json')

    sender = manager_util.sanitize_tag(sender)
    msg = manager_util.sanitize_tag(msg)
    target = core.lookup_customnode_by_url(json_obj, custom_node_url)

    if target is not None:
        PromptServer.instance.send_sync("cm-api-try-install-customnode",
                                        {"sender": sender, "target": target, "msg": msg})
    else:
        print(f"[ComfyUI Manager API] Failed to try install - Unknown custom node url '{custom_node_url}'")


def confirm_try_install(sender, custom_node_url, msg):
    asyncio.run(_confirm_try_install(sender, custom_node_url, msg))


cm_global.register_api('cm.try-install-custom-node', confirm_try_install)

import asyncio


async def default_cache_update():
    async def get_cache(filename):
        uri = f"{core.DEFAULT_CHANNEL}/{filename}"
        cache_uri = str(manager_util.simple_hash(uri)) + '_' + filename
        cache_uri = os.path.join(core.cache_dir, cache_uri)

        json_obj = await manager_util.get_data(uri, True)

        with core.cache_lock:
            with open(cache_uri, "w", encoding='utf-8') as file:
                json.dump(json_obj, file, indent=4, sort_keys=True)
                print(f"[ComfyUI-Manager] default cache updated: {uri}")

    a = get_cache("custom-node-list.json")
    b = get_cache("extension-node-map.json")
    e = get_cache("github-stats.json")

    await asyncio.gather(a, b, e)

    if not core.get_config()['skip_migration_check']:
        await core.check_need_to_migrate()
    else:
        print("[ComfyUI-Manager] Migration check is skipped...")


threading.Thread(target=lambda: asyncio.run(default_cache_update())).start()

if not os.path.exists(core.config_path):
    core.get_config()
    core.write_config()


cm_global.register_extension('manager-core',
                             {'version': core.version,
                                 'name': 'ComfyUI Manager (Essential)',
                                 'nodes': {},
                                 'description': 'ComfyUI-Manager (Essential)', })

if 'manager-core.show_menu' not in cm_global.variables:
    cm_global.variables['manager-core.show_menu'] = True

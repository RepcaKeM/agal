from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any
import yaml

from agal import __version__, ui
from agal.config import (
    AGAL_CONTEXT_MARKER,
    get_config_path,
    get_presets_dir,
    get_sources_dir,
    load_config,
)
from agal.hooks import install_hook, uninstall_hook
from agal.mcp import install_mcp, uninstall_mcp
from agal.presets import (
    create_preset_interactive,
    delete_preset,
    edit_preset,
    install_preset,
    list_presets,
    resolve_preset,
    uninstall_preset,
    _select_items_cli,
)
from agal.skills import (
    install_skill,
    load_global_state,
    load_local_state,
    uninstall_skill,
)
from agal.sources import (
    add_source,
    derive_source_name,
    detect_source_binaries,
    get_all_hooks,
    get_all_mcp_servers,
    get_all_skills,
    install_source_binaries,
    list_sources,
    load_sources_registry,
    remove_source,
    save_sources_registry,
)
from agal.updater import (
    check_for_updates,
    format_update_notice,
    update_sources,
)


def _print_update_notice(cfg: dict[str, Any]) -> None:
    try:
        updates = check_for_updates(force=False, timeout_sec=1.5, cfg=cfg)
        notice = format_update_notice(updates)
        if notice:
            print(f"\n{ui.notice_banner(notice)}\n")
    except Exception:
        pass


def _check_missing_tools_notice(source_name: str) -> None:
    try:
        sources = load_sources_registry()
        if source_name in sources:
            sdata = sources[source_name]
            src_path = Path(sdata.get("path", ""))
            if src_path.is_dir():
                detected = detect_source_binaries(src_path)
                installed = sdata.get("binaries", [])
                missing = [t for t in detected if t not in installed]
                if missing:
                    print(f"💡 Note: Source '{source_name}' provides CLI tool(s): {', '.join(missing)} (not installed).")
                    print(f"   To install into isolated venv, run: agal source install-tools {source_name}")
    except Exception:
        pass


def cmd_source(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    action = args.source_action
    if action == "add":
        source_name = args.name or derive_source_name(args.url)
        sources_dir = get_sources_dir(cfg)
        target_path = sources_dir / source_name
        force = getattr(args, "force", False)

        if target_path.exists() and not force:
            if sys.stdin.isatty():
                print(f"\n⚠️  Source '{source_name}' already exists ({target_path}).")
                try:
                    ans = input("   Do you want to re-download and overwrite it? [y/N]: ").strip().lower()
                    if ans in ("y", "yes", "tak", "t"):
                        force = True
                    else:
                        print("   Aborted.")
                        return
                except (EOFError, KeyboardInterrupt):
                    print("\n   Aborted.")
                    return
            else:
                print(f"⚠️  Source '{source_name}' already exists ({target_path}).")
                print(f"   Use --force to overwrite, or run 'agal source update {source_name}'.")
                return

        print(f"📦 Adding source from: {args.url}")
        install_flag = None
        if getattr(args, "yes", False):
            install_flag = True
        elif getattr(args, "no_tools", False):
            install_flag = False

        try:
            res = add_source(
                args.url,
                name=args.name,
                branch=args.branch,
                cfg=cfg,
                install_tools=install_flag,
                force=force,
            )
        except Exception as e:
            print(f"❌ Error adding source: {e}")
            return

        indexed = res["indexed"]
        print(f"\n✅ Successfully added source '{res['name']}' (commit: {res['head_commit'][:7]})")
        print(f"   · Skills:  {len(indexed['skills'])} discovered")
        print(f"   · MCP:     {len(indexed['mcp_servers'])} discovered")
        print(f"   · Hooks:   {len(indexed['hooks'])} discovered")
        if res.get("binaries"):
            print(f"   · Tools:   {', '.join(res['binaries'])} installed into ~/.local/bin (Ready to use!)")
        elif res.get("available_tools"):
            print(f"   · Tools:   {', '.join(res['available_tools'])} available (run 'agal source install-tools {res['name']}')")

    elif action == "remove":
        if remove_source(args.name, cfg=cfg):
            print(f"✅ Removed source '{args.name}'")
        else:
            print(f"⚠️  Source '{args.name}' not found.")

    elif action in ("list", None):
        sources = list_sources(cfg)
        if not sources:
            print("No sources registered. Add one with: agal source add <git-url>")
            return
        print(f"\n{'Name':<18} {'Branch':<8} {'Commit':<10} {'Skills':<8} {'MCP':<6} {'Tools':<12} {'URL'}")
        print("─" * 85)
        for s in sources:
            c = s.get("head_commit", "")[:7] or "none"
            tools_str = ", ".join(s.get("binaries", [])) or "-"
            print(f"  {s['name']:<16} {s.get('branch', 'main'):<8} {c:<10} {s.get('skills_count', 0):<8} {s.get('mcp_count', 0):<6} {tools_str:<12} {s.get('url', '')}")
        print()

    elif action == "update":
        targets = [args.name] if args.name else None
        print(f"🔄 Checking and updating sources...")
        summary = update_sources(targets, cfg=cfg)
        for sname, res in summary.items():
            if res.get("success"):
                diff_skills = f" (+{res['skills_diff']})" if res.get("skills_diff") else ""
                diff_mcp = f" (+{res['mcp_diff']})" if res.get("mcp_diff") else ""
                print(f"  ✅ {sname}: updated {res['old_commit']} → {res['new_commit']} (Skills: {res['skills_count']}{diff_skills}, MCP: {res['mcp_count']}{diff_mcp})")
            else:
                print(f"  ⚠️  {sname}: {res.get('error')}")

    elif action == "install-tools":
        sources = load_sources_registry()
        if args.name not in sources:
            print(f"⚠️  Source '{args.name}' not found in registered sources: {', '.join(sources.keys()) or 'none'}")
            return
        sinfo = sources[args.name]
        src_path = Path(sinfo.get("path", ""))
        if not src_path.is_dir():
            print(f"⚠️  Source directory does not exist: {src_path}")
            return
        tools = detect_source_binaries(src_path)
        if not tools:
            print(f"ℹ️  No executable tools detected in source '{args.name}'.")
            return
        tools_str = ", ".join(f"'{t}'" for t in tools)
        print(f"\n⚡ Detected CLI tool(s) in '{args.name}': {tools_str}")
        print(f"   Installing into isolated environment (~/.agal/venv)...")
        bins = install_source_binaries(src_path)
        if bins:
            sources[args.name]["binaries"] = bins
            save_sources_registry(sources)
            print(f"✅ Successfully installed and symlinked: {', '.join(bins)} -> ~/.local/bin")
        else:
            print(f"⚠️  Failed to install tools from {src_path}.")


def cmd_add(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    item_type = args.item_type
    name = args.name
    scope = "global" if args.global_scope else "local"
    copy = getattr(args, "copy", False)

    try:
        if item_type == "skill":
            res = install_skill(name, scope=scope, copy=copy, cfg=cfg)
            mode_str = "copied" if copy else "symlinked"
            print(f"✅ Installed skill '{name}' ({mode_str}, scope: {scope}) from source '{res['source']}'")
            _check_missing_tools_notice(res["source"])

        elif item_type == "mcp":
            res = install_mcp(name, scope=scope, cfg=cfg)
            print(f"✅ Installed MCP server '{name}' (scope: {scope}) from source '{res['source']}'")
            _check_missing_tools_notice(res["source"])

        elif item_type == "hook":
            res = install_hook(name, scope=scope, cfg=cfg)
            print(f"✅ Installed hook '{name}' (scope: {scope}) from source '{res['source']}'")

        elif item_type == "preset":
            res = install_preset(name, scope=scope, copy=copy, cfg=cfg)
            print(f"\n✅ Installed preset '{name}' (scope: {scope}):")
            print(f"   · Skills: {len(res['skills'])} installed")
            print(f"   · MCP:    {len(res['mcp'])} configured")
            print(f"   · Hooks:  {len(res['hooks'])} installed")
            if res.get("guidelines"):
                print(f"   · Guidelines placed: {', '.join(res['guidelines'])}")
            print()
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ {e}")


def cmd_remove(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    item_type = args.item_type
    name = args.name
    scope = "global" if args.global_scope else "local"

    if item_type == "skill":
        if uninstall_skill(name, scope=scope):
            print(f"✅ Uninstalled skill '{name}' (scope: {scope})")
        else:
            print(f"⚠️  Skill '{name}' was not installed.")

    elif item_type == "mcp":
        if uninstall_mcp(name, scope=scope):
            print(f"✅ Uninstalled MCP server '{name}' (scope: {scope})")
        else:
            print(f"⚠️  MCP server '{name}' was not installed.")

    elif item_type == "hook":
        if uninstall_hook(name, scope=scope):
            print(f"✅ Uninstalled hook '{name}' (scope: {scope})")
        else:
            print(f"⚠️  Hook '{name}' was not installed.")

    elif item_type == "preset":
        if scope == "local":
            res = uninstall_preset(scope=scope, cfg=cfg)
            print(f"\n✅ Uninstalled preset:")
            print(f"   · Skills removed: {len(res['removed_skills'])}")
            print(f"   · MCP removed:    {len(res['removed_mcp'])}")
            print(f"   · Hooks removed:  {len(res['removed_hooks'])}")
            if res.get("removed_context"):
                print(f"   · Guidelines removed: {', '.join(res['removed_context'])}")
            print()
        else:
            print("⚠️  Global preset removal should specify individual items: agal remove skill <name> --global")


def cmd_list(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    cat = args.category or "all"

    if cat in ("skills", "all"):
        skills = get_all_skills(cfg)
        print(f"\n📦 Available Skills ({len(skills)}):")
        print("─" * 60)
        for sname, sinfo in sorted(skills.items()):
            src = sinfo.get("source", "unknown")
            desc = sinfo.get("description", "")
            desc_short = (desc[:45] + "...") if len(desc) > 45 else desc
            print(f"  · {sname:<32} [{src}]  {desc_short}")
        print()

    if cat in ("mcp", "all"):
        mcp = get_all_mcp_servers(cfg)
        print(f"🔌 Available MCP Servers ({len(mcp)}):")
        print("─" * 60)
        for mname, minfo in sorted(mcp.items()):
            src = minfo.get("source", "unknown")
            mcfg = minfo.get("config", {})
            if "url" in mcfg:
                print(f"  · {mname:<32} [{src}]  url: {mcfg['url']}")
            else:
                print(f"  · {mname:<32} [{src}]  command: {mcfg.get('command', '')}")
        print()

    if cat in ("hooks", "all"):
        hooks = get_all_hooks(cfg)
        if hooks or cat == "hooks":
            print(f"🪝 Available Hooks ({len(hooks)}):")
            print("─" * 60)
            for hname, hinfo in sorted(hooks.items()):
                src = hinfo.get("source", "unknown")
                exe = " (executable)" if hinfo.get("executable") else ""
                print(f"  · {hname:<32} [{src}]{exe}")
            print()

    if cat in ("presets", "all"):
        presets = list_presets(cfg)
        print(f"📋 Available Presets ({len(presets)}):")
        print("─" * 60)
        for p in presets:
            print(f"  · {p['name']:<24} (Skills: {p['skills_count']}, MCP: {p['mcp_count']}) — {p['description']}")
        print()

    if cat in ("sources", "all"):
        sources = list_sources(cfg)
        if sources or cat == "sources":
            print(f"🌐 Registered Git Sources ({len(sources)}):")
            print("─" * 85)
            if not sources:
                print("  (No sources registered. Add one with: agal source add <git-url>)")
            else:
                print(f"  {'Name':<16} {'Branch':<8} {'Commit':<10} {'Skills':<8} {'MCP':<6} {'Tools':<12} {'URL'}")
                for s in sources:
                    c = s.get("head_commit", "")[:7] or "none"
                    tools_str = ", ".join(s.get("binaries", [])) or "-"
                    print(f"  {s['name']:<16} {s.get('branch', 'main'):<8} {c:<10} {s.get('skills_count', 0):<8} {s.get('mcp_count', 0):<6} {tools_str:<12} {s.get('url', '')}")
            print()


def cmd_preset(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    action = args.preset_action
    if action == "create":
        create_preset_interactive(args.name, cfg=cfg)
    elif action == "list":
        cmd_list(argparse.Namespace(category="presets"), cfg)
    elif action == "info":
        try:
            p = resolve_preset(args.name, cfg)
            all_skills = get_all_skills(cfg)
            all_mcp = get_all_mcp_servers(cfg)

            print(f"\n📋 {ui.bold('Preset:')} {ui.cyan(p['name'])}")
            if p.get("description"):
                print(f"   {ui.dim(p.get('description'))}\n")

            skills = p.get("skills", [])
            print(f"  📦 {ui.bold('Skills')} ({len(skills)}):")
            if skills:
                for s in skills:
                    if s in all_skills:
                        src = all_skills[s].get("source", "unknown")
                        print(f"     {ui.ok_mark()} {ui.bold(s):<32} {ui.dim(f'[{src}]')}")
                    else:
                        print(f"     {ui.fail_mark()} {ui.bold(s):<32} {ui.yellow('[missing source — run: agal source add <url>]')}")
            else:
                print(f"     {ui.dim('(none)')}")

            mcp_list = p.get("mcp", [])
            print(f"\n  🔌 {ui.bold('MCP Servers')} ({len(mcp_list)}):")
            if mcp_list:
                for m in mcp_list:
                    if m in all_mcp:
                        cmd = all_mcp[m].get("config", {}).get("command", "")
                        print(f"     {ui.ok_mark()} {ui.bold(m):<32} {ui.dim(f'(command: {cmd})')}")
                    else:
                        print(f"     {ui.fail_mark()} {ui.bold(m):<32} {ui.yellow('[missing definition]')}")
            else:
                print(f"     {ui.dim('(none)')}")
            print()
        except Exception as e:
            print(f"⚠️  Error: {e}")
    elif action in ("delete", "remove"):
        presets_dir = get_presets_dir(cfg)
        target_file = presets_dir / f"{args.name}.yaml"
        if not target_file.is_file():
            target_file = presets_dir / f"{args.name}.yml"

        if not target_file.is_file():
            print(f"⚠️  Preset '{args.name}' not found in {presets_dir}")
            return

        if not getattr(args, "yes", False):
            ans = input(f"Are you sure you want to delete preset '{args.name}'? [y/N]: ").strip().lower()
            if ans not in ("y", "yes"):
                print("Cancelled.")
                return

        if delete_preset(args.name, cfg=cfg):
            print(f"✅ Deleted preset '{args.name}' ({target_file.name})")
        else:
            print(f"⚠️  Failed to delete preset '{args.name}'.")
    elif action == "edit":
        try:
            target_file = edit_preset(args.name, cfg=cfg)
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    skills_count = len(data.get("skills", []))
                    mcp_count = len(data.get("mcp", []))
                    print(f"✅ Preset '{args.name}' saved ({skills_count} skills, {mcp_count} MCP).")
            except Exception as e:
                print(f"⚠️  Warning: Preset contains YAML syntax errors: {e}")
        except FileNotFoundError as e:
            print(f"⚠️  {e}")


def cmd_check(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    print("\n🔍 Checking skills and updates...")

    # 1. Update check
    updates = check_for_updates(force=True, timeout_sec=3.0, cfg=cfg)
    if updates:
        print("\n💡 Available Updates:")
        for sname, u in updates.items():
            print(f"  · {sname}: {u['local']} → {u['remote']} (Run 'agal update {sname}')")
    else:
        print("  ✅ All registered sources are up-to-date.")

    # 2. Frontmatter validation
    all_skills = get_all_skills(cfg)
    ok_count = 0
    missing_desc = []
    missing_name = []

    for sname, sinfo in all_skills.items():
        desc = sinfo.get("description", "")
        name = sinfo.get("name", "")
        if name and desc:
            ok_count += 1
        elif not name:
            missing_name.append(sname)
        elif not desc:
            missing_desc.append(sname)

    print(f"\n📊 Skills Validation ({len(all_skills)} total across sources):")
    print(f"  ✅ OK (name + description): {ok_count}")
    if missing_desc:
        print(f"  ⚠️  Missing description:    {len(missing_desc)} ({', '.join(missing_desc[:5])})")
    if missing_name:
        print(f"  ⚠️  Missing name:           {len(missing_name)}")

    # 3. Active in cwd
    cwd = Path.cwd()
    state = load_local_state(cwd)
    local_skills = state.get("skills", {})
    local_mcp = state.get("mcp", {})

    print(f"\n📂 Active in Current Directory ({cwd.name}):")
    if local_skills:
        print("  Skills:")
        for s in sorted(local_skills.keys()):
            print(f"    · {s}")
    else:
        print("  (No skills currently managed in cwd)")

    if local_mcp:
        print("  MCP Servers:")
        for m in sorted(local_mcp.keys()):
            print(f"    · {m}")
    print()


def cmd_status(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    cwd = Path.cwd()
    local_state = load_local_state(cwd)
    global_state = load_global_state()
    preset = local_state.get("preset")

    rows = [
        ("Project Path:", str(cwd)),
        ("Active Preset:", ui.green(f"● {preset}") if preset else ui.dim("none")),
    ]
    print("\n" + ui.card(f"AGAL  ›  Agent Agnostic Launch v{__version__}", rows))

    l_skills = local_state.get("skills", {})
    print(f"\n  📦 {ui.bold('Project Skills')} ({len(l_skills)}):")
    if l_skills:
        for sname, sdata in sorted(l_skills.items()):
            src = sdata.get("source", "unknown")
            mode = sdata.get("mode", "symlink")
            mode_str = "🔗 symlink" if mode == "symlink" else "📋 copy"
            print(f"     {ui.ok_mark()} {ui.bold(sname):<32} {ui.dim(f'[{mode_str}]')} {ui.dim(f'(source: {src})')}")
    else:
        print(f"     {ui.dim('(none — run: agal prepare <preset> or agal add skill <name>)')}")

    l_mcp = local_state.get("mcp", {})
    print(f"\n  🔌 {ui.bold('Project MCP Servers')} ({len(l_mcp)}):")
    if l_mcp:
        for mname, mdata in sorted(l_mcp.items()):
            cmd = mdata.get("config", {}).get("command", "")
            args_list = mdata.get("config", {}).get("args", [])
            full_cmd = f"{cmd} {' '.join(args_list)}".strip()
            cmd_short = (full_cmd[:45] + "...") if len(full_cmd) > 45 else full_cmd
            print(f"     {ui.ok_mark()} {ui.bold(mname):<28} {ui.dim(f'(command: {cmd_short})')}")
    else:
        print(f"     {ui.dim('(none — run: agal add mcp <name>)')}")

    marker = cwd / AGAL_CONTEXT_MARKER
    print(f"\n  🧠 {ui.bold('Coding Guidelines')}:")
    if marker.is_file():
        files = marker.read_text().split()
        print(f"     {ui.ok_mark()} {ui.green('Active:')} {', '.join(files)}")
    else:
        if (cwd / "AGENTS.md").is_file():
            print(f"     {ui.ok_mark()} {ui.dim('Custom AGENTS.md detected in project root')}")
        else:
            print(f"     {ui.dim('(none deployed in current directory)')}")

    g_skills = global_state.get("skills", {})
    g_mcp = global_state.get("mcp", {})
    if g_skills or g_mcp:
        print(f"\n  🌐 {ui.bold('Global User Environment')} (~/.claude):")
        if g_skills:
            print(f"     · Skills ({len(g_skills)}): {', '.join(sorted(g_skills.keys()))}")
        if g_mcp:
            print(f"     · MCP    ({len(g_mcp)}): {', '.join(sorted(g_mcp.keys()))}")
    print()


def cmd_prepare_alias(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    copy = getattr(args, "remote", False) or getattr(args, "copy", False)
    try:
        res = install_preset(args.preset, scope="local", copy=copy, cfg=cfg)
    except (ValueError, FileNotFoundError) as e:
        print(f"❌ {e}")
        return
    print(f"\n✅ Prepared preset '{args.preset}':")
    print(f"   · Skills: {len(res['skills'])} linked")
    print(f"   · MCP:    {len(res['mcp'])} configured")
    if res.get("guidelines"):
        print(f"   · Guidelines: {', '.join(res['guidelines'])}")
    print()


def cmd_unprepare_alias(args: argparse.Namespace, cfg: dict[str, Any]) -> None:
    res = uninstall_preset(scope="local", cfg=cfg)
    print(f"✅ Unprepared: removed {len(res['removed_skills'])} skills, {len(res['removed_mcp'])} MCP servers.")


def interactive_launcher(cfg: dict[str, Any], parser: argparse.ArgumentParser) -> None:
    """Interactive quick-actions dashboard when invoked without arguments in TTY."""
    cwd = Path.cwd()
    state = load_local_state(cwd)
    active_preset = state.get("preset")

    title = f"AGAL  ›  Agent Agnostic Launch v{__version__}"
    rows = [
        ("Project Path:", str(cwd)),
        ("Active Preset:", ui.green(f"● {active_preset}") if active_preset else ui.dim("none")),
    ]
    print("\n" + ui.card(title, rows))
    print(f"\n{ui.bold('What would you like to do?')}")
    print(f"  {ui.cyan('[1]')} 🚀 Prepare a preset in this project    {ui.dim('(agal prepare <name>)')}")
    print(f"  {ui.cyan('[2]')} 🧹 Clean / Unprepare this project      {ui.dim('(agal unprepare)')}")
    print(f"  {ui.cyan('[3]')} 🛠️  Create a new custom preset          {ui.dim('(agal preset create <name>)')}")
    print(f"  {ui.cyan('[4]')} 📋 Browse available skills & MCP       {ui.dim('(agal list)')}")
    print(f"  {ui.cyan('[5]')} 🌐 Manage connected Git sources        {ui.dim('(agal source list)')}")
    print(f"  {ui.cyan('[6]')} 📊 View full project status            {ui.dim('(agal status)')}")
    print(f"  {ui.cyan('[7]')} ❓ Show full CLI help                  {ui.dim('(--help)')}")
    print(f"  {ui.dim('[0] Exit')}\n")

    try:
        choice = input(ui.bold("Select [1-7] > ")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if choice == "1":
        presets = list_presets(cfg)
        if not presets:
            print(f"\n{ui.warn_mark()} No presets found. Create one with: agal preset create <name>")
            return
        preset_names = [p["name"] for p in presets]
        display_labels = [f"{p['name']:<24} {ui.dim(p.get('description', ''))}" for p in presets]
        selected = _select_items_cli(preset_names, "Select preset to prepare", display_labels)
        if selected:
            cmd_prepare_alias(argparse.Namespace(preset=selected[0], remote=False, copy=False), cfg)
    elif choice == "2":
        cmd_unprepare_alias(argparse.Namespace(), cfg)
    elif choice == "3":
        try:
            pname = input("\nEnter new preset name: ").strip()
            if pname:
                cmd_preset(argparse.Namespace(preset_action="create", name=pname), cfg)
        except (EOFError, KeyboardInterrupt):
            print()
    elif choice == "4":
        cmd_list(argparse.Namespace(category="all"), cfg)
    elif choice == "5":
        cmd_source(argparse.Namespace(source_action="list"), cfg)
    elif choice == "6":
        cmd_status(argparse.Namespace(), cfg)
    elif choice == "7":
        parser.print_help()
    else:
        return


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    cfg = load_config()

    parser = argparse.ArgumentParser(
        prog="agal",
        description=f"agal v{__version__} — Agent Agnostic Launch (Skills & MCP Manager)",
    )
    parser.add_argument("--version", "-v", action="version", version=f"agal {__version__}")

    # Backward-compatible flags
    parser.add_argument("--status", action="store_true", help="Show active skills & preset status")
    parser.add_argument("--list", action="store_true", help="List available presets")
    parser.add_argument("--check", action="store_true", help="Check skill frontmatter and updates")
    parser.add_argument("--config", action="store_true", help="Print config file path")
    parser.add_argument("--edit", "-e", metavar="PRESET", help="Edit preset in $EDITOR")
    parser.add_argument("--prepare", metavar="PRESET", help="Prepare a preset in current project")
    parser.add_argument("--remote", "-r", action="store_true", help="Copy files instead of symlinking")
    parser.add_argument("--unprepare", action="store_true", help="Remove prepared preset from current project")

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand")

    # source
    p_source = subparsers.add_parser("source", help="Manage git sources")
    p_source_sub = p_source.add_subparsers(dest="source_action")
    p_sadd = p_source_sub.add_parser("add", help="Add git repository source")
    p_sadd.add_argument("url", help="Git repository URL")
    p_sadd.add_argument("--name", help="Custom name for the source")
    p_sadd.add_argument("--branch", default="main", help="Git branch (default: main)")
    p_sadd.add_argument("--yes", "-y", action="store_true", help="Automatically accept installing detected CLI tools")
    p_sadd.add_argument("--no-tools", action="store_true", help="Skip installing detected CLI tools without prompting")
    p_sadd.add_argument("--force", "-f", action="store_true", help="Overwrite source if it already exists")

    p_srem = p_source_sub.add_parser("remove", help="Remove source")
    p_srem.add_argument("name", help="Source name")

    p_slist = p_source_sub.add_parser("list", help="List registered sources")

    p_supd = p_source_sub.add_parser("update", help="Update sources")
    p_supd.add_argument("name", nargs="?", help="Specific source name (optional)")

    p_sinst = p_source_sub.add_parser("install-tools", help="Install CLI tools for a registered source")
    p_sinst.add_argument("name", help="Source name")

    # add
    p_add = subparsers.add_parser("add", help="Install a skill, MCP, hook, or preset")
    p_add.add_argument("item_type", choices=["skill", "mcp", "hook", "preset"])
    p_add.add_argument("name", help="Name of item to install")
    p_add.add_argument("--global", "-g", dest="global_scope", action="store_true", help="Install globally for user")
    p_add.add_argument("--copy", "-c", action="store_true", help="Copy instead of symlink")

    # remove
    p_rem = subparsers.add_parser("remove", help="Uninstall a skill, MCP, hook, or preset")
    p_rem.add_argument("item_type", choices=["skill", "mcp", "hook", "preset"])
    p_rem.add_argument("name", help="Name of item to uninstall")
    p_rem.add_argument("--global", "-g", dest="global_scope", action="store_true", help="Uninstall from global scope")

    # list
    p_list = subparsers.add_parser("list", help="List skills, MCP servers, or presets")
    p_list.add_argument("category", nargs="?", choices=["skills", "mcp", "hooks", "presets", "sources", "all"], default="all")

    # preset
    p_pre = subparsers.add_parser("preset", help="Manage skill/MCP presets")
    p_pre_sub = p_pre.add_subparsers(dest="preset_action")
    p_pcreate = p_pre_sub.add_parser("create", help="Create new preset")
    p_pcreate.add_argument("name", help="Preset name")
    p_plist = p_pre_sub.add_parser("list", help="List presets")
    p_pinfo = p_pre_sub.add_parser("info", help="Show preset info")
    p_pinfo.add_argument("name", help="Preset name")
    p_pdel = p_pre_sub.add_parser("delete", aliases=["remove"], help="Delete a preset")
    p_pdel.add_argument("name", help="Preset name")
    p_pdel.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    p_pedit = p_pre_sub.add_parser("edit", help="Edit preset in $EDITOR")
    p_pedit.add_argument("name", help="Preset name")

    # update
    p_upd = subparsers.add_parser("update", help="Update git sources")
    p_upd.add_argument("name", nargs="?", help="Specific source name")

    # prepare (subcommand alias)
    p_prep = subparsers.add_parser("prepare", help="Prepare a preset in current project")
    p_prep.add_argument("preset", help="Preset name")
    p_prep.add_argument("--remote", "-r", action="store_true", help="Copy files instead of symlinking")

    # unprepare (subcommand alias)
    subparsers.add_parser("unprepare", help="Remove prepared preset from current project")

    # check
    subparsers.add_parser("check", help="Check skill metadata and updates")

    # status
    subparsers.add_parser("status", help="Show active skills & preset status")

    # Pre-parse shortcut: if argv[0] is a known preset name and not a flag or subcommand
    known_commands = {
        "source", "add", "remove", "list", "preset", "update", "check", "status",
        "prepare", "unprepare", "-h", "--help", "-v", "--version", "--status",
        "--list", "--check", "--config", "--edit", "-e", "--prepare", "--unprepare",
    }
    if argv and argv[0] not in known_commands and not argv[0].startswith("-"):
        # Check if it matches a preset
        presets_dir = get_presets_dir(cfg)
        if (presets_dir / f"{argv[0]}.yaml").is_file() or (presets_dir / f"{argv[0]}.yml").is_file():
            # Rewrite to: prepare <argv[0]>
            argv = ["prepare", argv[0]] + argv[1:]

    args = parser.parse_args(argv)

    # Handle top-level flags
    if args.status:
        cmd_status(args, cfg)
        return
    if args.list and not args.subcommand:
        cmd_list(argparse.Namespace(category="presets"), cfg)
        return
    if args.check and not args.subcommand:
        cmd_check(args, cfg)
        return
    if args.config:
        print(f"Config path: {get_config_path()}")
        return
    if args.edit:
        cmd_preset(argparse.Namespace(preset_action="edit", name=args.edit), cfg)
        return
    if args.prepare:
        cmd_prepare_alias(args, cfg)
        return
    if args.unprepare:
        cmd_unprepare_alias(args, cfg)
        return

    # Check for background update suggestions (non-intrusive)
    _print_update_notice(cfg)

    if args.subcommand == "source":
        cmd_source(args, cfg)
    elif args.subcommand == "add":
        cmd_add(args, cfg)
    elif args.subcommand == "remove":
        cmd_remove(args, cfg)
    elif args.subcommand == "list":
        cmd_list(args, cfg)
    elif args.subcommand == "preset":
        cmd_preset(args, cfg)
    elif args.subcommand == "prepare":
        cmd_prepare_alias(args, cfg)
    elif args.subcommand == "unprepare":
        cmd_unprepare_alias(args, cfg)
    elif args.subcommand == "update":
        cmd_source(argparse.Namespace(source_action="update", name=args.name), cfg)
    elif args.subcommand == "check":
        cmd_check(args, cfg)
    elif args.subcommand == "status":
        cmd_status(args, cfg)
    else:
        # Default with no args: interactive launcher if TTY, else help
        if sys.stdin.isatty():
            interactive_launcher(cfg, parser)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()

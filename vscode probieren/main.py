#!/usr/bin/env python3
"""
RepoManager – Repository-Updater & -Ausleser mit ConstructionKit Integration
Integriert das ConstructionKit-Verwaltungstool in eine benutzerfreundliche Oberfläche.
"""
import sys
import os
import json
import re
import time
import requests
import base64
import fnmatch
from pathlib import Path

# ANSI-Farbcodes für die Konsole
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

# GitHub-Konfiguration
GITHUB_TOKEN = "..."  # Hier dein GitHub Token einfügen
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

def clear_screen():
    """Bildschirm leeren"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Schönen Banner mit Farben ausgeben"""
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}🚀 RepoManager – Repository-Updater & ConstructionKit Manager 🚀{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.GRAY}Ein mächtiges Tool für Repository- und ConstructionKit-Management{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")

def print_menu():
    """Menü mit Farben und Icons ausgeben"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}📋 HAUPTMENÜ{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    menu_items = [
        ("A", "🔍 ConstructionKit Versionen prüfen", Colors.GREEN),
        ("B", "📝 Config.json erstellen/bearbeiten", Colors.CYAN),
        ("C", "🔄 ConstructionKit Versionen updaten", Colors.YELLOW),
        ("D", "📊 Letzte Ergebnisse anzeigen", Colors.MAGENTA),
        ("E", "⚙️  GitHub Token konfigurieren", Colors.BLUE),
        ("F", "🚪 Exit", Colors.RED)
    ]
    
    for key, label, color in menu_items:
        print(f"{color}[{key}]{Colors.RESET} {label}")
    
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")

def get_branches(owner, repo, limit=None):
    """Branches eines Repositories abrufen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/branches"
    branches = []
    page = 1
    per_page = 30

    while True:
        params = {"per_page": per_page, "page": page}
        r = requests.get(url, headers=HEADERS, params=params)
        if r.status_code != 200:
            print(f"{Colors.RED}❌ Error fetching branches for {owner}/{repo}: {r.status_code} {r.text}{Colors.RESET}")
            break
        data = r.json()
        branches.extend([b["name"] for b in data])
        if len(data) < per_page or (limit and len(branches) >= limit):
            break
        page += 1

    return branches[:limit] if limit else branches

def get_file_content(owner, repo, path, branch):
    """Dateiinhalt von GitHub abrufen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        content = r.json()
        return base64.b64decode(content["content"]).decode(), content["sha"]
    return None, None

def find_constructionkit_version(content):
    """ConstructionKit Version aus Dateiinhalt extrahieren"""
    for line in content.splitlines():
        if line.strip().startswith("constructionkit/"):
            return line.strip()
    return None

def update_version_in_content(content, new_version):
    """Version in Dateiinhalt aktualisieren"""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("constructionkit/"):
            lines[i] = f"constructionkit/{new_version}@spx00/release"
    return "\n".join(lines)

def create_branch(owner, repo, base_branch, new_branch):
    """Neuen Branch erstellen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/git/refs/heads/{base_branch}"
    r = requests.get(url, headers=HEADERS)
    sha = r.json()["object"]["sha"]
    data = {"ref": f"refs/heads/{new_branch}", "sha": sha}
    requests.post(f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/git/refs", headers=HEADERS, json=data)

def update_file(owner, repo, path, content, sha, branch, message):
    """Datei in GitHub aktualisieren"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/contents/{path}"
    data = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha,
        "branch": branch
    }
    requests.put(url, headers=HEADERS, json=data)

def create_pull_request(owner, repo, head, base, title, body):
    """Pull Request erstellen"""
    url = f"https://github.psa-cloud.com/api/v3/repos/{owner}/{repo}/pulls"
    data = {"title": title, "head": head, "base": base, "body": body}
    r = requests.post(url, headers=HEADERS, json=data)
    return r.json()["html_url"]

def check_constructionkit_versions():
    """ConstructionKit Versionen in allen konfigurierten Repositories prüfen"""
    print(f"\n{Colors.BOLD}{Colors.GREEN}🔍 CONSTRUCTIONKIT VERSIONEN PRÜFEN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    if not GITHUB_TOKEN or GITHUB_TOKEN == "...":
        print(f"{Colors.RED}❌ GitHub Token nicht konfiguriert!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst Token in Option E konfigurieren.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    config_file = "config.json"
    if not os.path.exists(config_file):
        print(f"{Colors.RED}❌ config.json nicht gefunden!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst Config-Datei in Option B erstellen.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    try:
        with open(config_file) as f:
            config = json.load(f)
        
        recipe_path = config["recipe_path"]
        branch_pattern = config["branch_pattern"]
        
        print(f"{Colors.YELLOW}📋 Konfiguration:{Colors.RESET}")
        print(f"  Recipe Path: {Colors.CYAN}{recipe_path}{Colors.RESET}")
        print(f"  Branch Pattern: {Colors.CYAN}{branch_pattern}{Colors.RESET}")
        print(f"  Repositories: {Colors.CYAN}{len(config['repos'])}{Colors.RESET}")
        
        output = {"recipe_path": recipe_path, "output": {}}
        
        for repo_full in config["repos"]:
            print(f"\n{Colors.BOLD}🔄 Prüfe {repo_full}...{Colors.RESET}")
            owner, repo = repo_full.split("/")
            
            try:
                branches = get_branches(owner, repo)
                matching_branches = [b for b in branches if fnmatch.fnmatch(b, branch_pattern)]
                
                print(f"  {Colors.GREEN}✓ Gefundene Branches: {len(matching_branches)}{Colors.RESET}")
                
                output['output'][repo_full] = {
                    "fixed_versions": [],
                    "latest_versions": [],
                    "unknown_versions": []
                }
                
                for branch in matching_branches:
                    content, sha = get_file_content(owner, repo, recipe_path, branch)
                    if not content:
                        print(f"    {Colors.RED}❌ {branch}: Datei nicht gefunden{Colors.RESET}")
                        output['output'][repo_full]["unknown_versions"].append((branch, ''))
                        continue
                    
                    current_version = find_constructionkit_version(content)
                    if current_version:
                        print(f"    {Colors.GREEN}✓ {branch}: {current_version}{Colors.RESET}")
                        
                        # Fixed versions prüfen
                        if re.findall(r"^.*\[(\d+\.\d+\.\d+|>\d+\.\d+\.\d+\s*<\d+\.\d+\.\d+|\d+\.\d+\.\d+\s*\|\|\s*>\d+\.\d+\.\d+\s*<\d+\.\d+\.\d+)].*$", current_version) or \
                           re.findall(r"^.*/\d+\.\d+\.\d+@.*$", current_version):
                            output['output'][repo_full]["fixed_versions"].append((branch, current_version))
                        # Latest versions prüfen
                        elif re.findall(r"^.*\[>=\d+\.\d+\.\d+].*$", current_version):
                            output['output'][repo_full]["latest_versions"].append((branch, current_version))
                        else:
                            output['output'][repo_full]["unknown_versions"].append((branch, current_version))
                    else:
                        print(f"    {Colors.YELLOW}⚠️  {branch}: Keine ConstructionKit Version gefunden{Colors.RESET}")
                        output['output'][repo_full]["unknown_versions"].append((branch, ''))
                    
                    time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"    {Colors.RED}❌ Fehler bei {repo_full}: {e}{Colors.RESET}")
            
            time.sleep(0.5)  # Rate limiting
        
        # Ergebnisse speichern
        with open("output.json", "w") as f:
            json.dump(output, f, indent=4)
        
        print(f"\n{Colors.GREEN}✅ Prüfung abgeschlossen!{Colors.RESET}")
        print(f"{Colors.CYAN}Ergebnisse in output.json gespeichert.{Colors.RESET}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler: {e}{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def create_edit_config():
    """Config.json erstellen oder bearbeiten"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}📝 CONFIG.JSON ERSTELLEN/BEARBEITEN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    # Standard-Repositories (alle verfügbaren)
    default_repos = [
        "spx01/STLA.BSW.ZCU_CL",
        "spx01/STLA.FBL.ZCU_Rear"
    ]
    
    # Aktuelle Konfiguration laden, falls vorhanden
    config_file = "config.json"
    if os.path.exists(config_file):
        print(f"{Colors.YELLOW}📋 Aktuelle Konfiguration gefunden.{Colors.RESET}")
        try:
            with open(config_file) as f:
                config = json.load(f)
            print(f"  Recipe Path: {Colors.CYAN}{config.get('recipe_path', 'N/A')}{Colors.RESET}")
            print(f"  Branch Pattern: {Colors.CYAN}{config.get('branch_pattern', 'N/A')}{Colors.RESET}")
            print(f"  Repositories: {Colors.CYAN}{len(config.get('repos', []))}{Colors.RESET}")
        except:
            config = {}
    else:
        config = {}
    
    print(f"\n{Colors.YELLOW}Konfiguration bearbeiten (Enter für Standard-Werte):{Colors.RESET}")
    
    # Recipe Path - angepasst an deine Konfiguration
    current_recipe = config.get("recipe_path", "conanrecipe_ckit.txt")
    recipe_path = input(f"Recipe Path [{Colors.CYAN}{current_recipe}{Colors.RESET}]: ").strip()
    if not recipe_path:
        recipe_path = current_recipe
    
    # Branch Pattern - angepasst an deine Konfiguration
    current_pattern = config.get("branch_pattern", "release/*")
    branch_pattern = input(f"Branch Pattern [{Colors.CYAN}{current_pattern}{Colors.RESET}]: ").strip()
    if not branch_pattern:
        branch_pattern = current_pattern
    
    # Repositories - angepasst an deine Konfiguration
    print(f"\n{Colors.YELLOW}Repository-Konfiguration:{Colors.RESET}")
    print(f"[1] Alle verfügbaren Repositories ({len(default_repos)} Repos)")
    print(f"[2] Aktuelle Konfiguration beibehalten")
    print(f"[3] Nur Test-Repositories (ZCU_CL, ZCU_CR)")
    print(f"[4] Eigene Repositories eingeben")
    
    choice = input(f"Auswahl [3]: ").strip()
    
    if choice == "1":
        repos = default_repos
    elif choice == "2" and config.get("repos"):
        repos = config["repos"]
    elif choice == "4":
        repos = []
        print(f"\n{Colors.YELLOW}Repositories eingeben (leer für Ende):{Colors.RESET}")
        while True:
            repo = input(f"Repository (org/name): ").strip()
            if not repo:
                break
            repos.append(repo)
    else:
        # Standard: Test-Repositories wie in deiner config.json
        repos = [
            "spx01/STLA.BSW.ZCU_CL",
            "spx01/STLA.BSW.ZCU_CR"
        ]
    
    # Konfiguration zusammenstellen
    new_config = {
        "recipe_path": recipe_path,
        "branch_pattern": branch_pattern,
        "repos": repos
    }
    
    # Speichern
    try:
        with open(config_file, "w") as f:
            json.dump(new_config, f, indent=4)
        
        print(f"\n{Colors.GREEN}✅ Konfiguration gespeichert!{Colors.RESET}")
        print(f"{Colors.CYAN}Datei: {config_file}{Colors.RESET}")
        print(f"{Colors.CYAN}Repositories: {len(repos)}{Colors.RESET}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler beim Speichern: {e}{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def update_constructionkit_versions():
    """ConstructionKit Versionen updaten und Pull Requests erstellen"""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}🔄 CONSTRUCTIONKIT VERSIONEN UPDATEN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    if not GITHUB_TOKEN or GITHUB_TOKEN == "...":
        print(f"{Colors.RED}❌ GitHub Token nicht konfiguriert!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst Token in Option E konfigurieren.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    output_file = "output.json"
    if not os.path.exists(output_file):
        print(f"{Colors.RED}❌ output.json nicht gefunden!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst Versionen in Option A prüfen.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    # Neue Version eingeben
    new_version = input(f"{Colors.YELLOW}Neue ConstructionKit Version (z.B. 1.44.0): {Colors.RESET}").strip()
    if not new_version:
        print(f"{Colors.RED}❌ Keine Version eingegeben!{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    try:
        with open(output_file) as f:
            config = json.load(f)
        
        recipe_path = config["recipe_path"]
        list_of_prs = []
        
        print(f"\n{Colors.YELLOW}🔄 Aktualisiere auf Version: {new_version}{Colors.RESET}")
        
        for repo_full, branches_info in config['output'].items():
            if not branches_info["latest_versions"]:
                print(f"{Colors.GRAY}⏭️  {repo_full}: Keine Latest-Versions gefunden{Colors.RESET}")
                continue
            
            print(f"\n{Colors.BOLD}🔄 Bearbeite {repo_full}...{Colors.RESET}")
            
            for branch, current_version in branches_info["latest_versions"]:
                try:
                    pr_branch = f"update-ckit-version-{branch}"
                    owner, repo = repo_full.split("/")
                    
                    print(f"  {Colors.YELLOW}🔄 {branch}: {current_version} → {new_version}{Colors.RESET}")
                    
                    # Branch erstellen
                    create_branch(owner, repo, branch, pr_branch)
                    
                    # Datei aktualisieren
                    content, sha = get_file_content(owner, repo, recipe_path, branch)
                    new_content = update_version_in_content(content, new_version)
                    update_file(owner, repo, recipe_path, new_content, sha, pr_branch,
                                f"Update constructionkit to {new_version}")
                    
                    # Pull Request erstellen
                    pr_url = create_pull_request(
                        owner, repo, pr_branch, branch,
                        f"Update constructionkit to {new_version}",
                        f"This PR updates constructionkit to version {new_version}."
                    )
                    
                    print(f"    {Colors.GREEN}✅ PR erstellt: {pr_url}{Colors.RESET}")
                    list_of_prs.append(pr_url)
                    
                except Exception as e:
                    print(f"    {Colors.RED}❌ Fehler: {e}{Colors.RESET}")
                
                time.sleep(1)  # Rate limiting
            
            time.sleep(1)  # Rate limiting
        
        # PR-Liste speichern
        if list_of_prs:
            with open("created_prs.txt", "w") as f:
                for pr in list_of_prs:
                    f.write(f"{pr}\n")
            
            print(f"\n{Colors.GREEN}✅ {len(list_of_prs)} Pull Requests erstellt!{Colors.RESET}")
            print(f"{Colors.CYAN}Liste gespeichert in: created_prs.txt{Colors.RESET}")
        else:
            print(f"\n{Colors.YELLOW}⚠️  Keine Pull Requests erstellt.{Colors.RESET}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler: {e}{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def show_last_results():
    """Letzte Ergebnisse anzeigen"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}📊 LETZTE ERGEBNISSE ANZEIGEN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    output_file = "output.json"
    if not os.path.exists(output_file):
        print(f"{Colors.RED}❌ Keine Ergebnisse gefunden!{Colors.RESET}")
        print(f"{Colors.YELLOW}Bitte erst Versionen in Option A prüfen.{Colors.RESET}")
        input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")
        return
    
    try:
        with open(output_file) as f:
            results = json.load(f)
        
        print(f"{Colors.YELLOW}📋 Ergebnisse für Recipe Path: {Colors.CYAN}{results['recipe_path']}{Colors.RESET}")
        
        for repo_full, branches_info in results['output'].items():
            print(f"\n{Colors.BOLD}📦 {repo_full}:{Colors.RESET}")
            
            # Fixed Versions
            if branches_info["fixed_versions"]:
                print(f"  {Colors.GREEN}🔒 Fixed Versions ({len(branches_info['fixed_versions'])}):{Colors.RESET}")
                for branch, version in branches_info["fixed_versions"]:
                    print(f"    {Colors.CYAN}{branch}{Colors.RESET}: {version}")
            
            # Latest Versions
            if branches_info["latest_versions"]:
                print(f"  {Colors.YELLOW}🔄 Latest Versions ({len(branches_info['latest_versions'])}):{Colors.RESET}")
                for branch, version in branches_info["latest_versions"]:
                    print(f"    {Colors.CYAN}{branch}{Colors.RESET}: {version}")
            
            # Unknown Versions
            if branches_info["unknown_versions"]:
                print(f"  {Colors.RED}❓ Unknown/Missing ({len(branches_info['unknown_versions'])}):{Colors.RESET}")
                for branch, version in branches_info["unknown_versions"]:
                    print(f"    {Colors.CYAN}{branch}{Colors.RESET}: {version or 'N/A'}")
        
        # PR-Liste anzeigen falls vorhanden
        pr_file = "created_prs.txt"
        if os.path.exists(pr_file):
            print(f"\n{Colors.BOLD}{Colors.GREEN}📋 Erstellte Pull Requests:{Colors.RESET}")
            with open(pr_file) as f:
                prs = f.read().strip().split('\n')
                for i, pr in enumerate(prs, 1):
                    if pr.strip():
                        print(f"  {i}. {Colors.CYAN}{pr}{Colors.RESET}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Fehler beim Lesen der Ergebnisse: {e}{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def configure_github_token():
    """GitHub Token konfigurieren"""
    global GITHUB_TOKEN, HEADERS
    
    print(f"\n{Colors.BOLD}{Colors.BLUE}⚙️  GITHUB TOKEN KONFIGURIEREN{Colors.RESET}")
    print(f"{Colors.BLUE}{'─'*50}{Colors.RESET}")
    
    print(f"{Colors.YELLOW}📋 Benötigte Berechtigungen:{Colors.RESET}")
    print(f"  • gist")
    print(f"  • project")
    print(f"  • repo")
    print(f"  • user")
    
    current_status = "✅ Konfiguriert" if GITHUB_TOKEN and GITHUB_TOKEN != "..." else "❌ Nicht konfiguriert"
    print(f"\n{Colors.YELLOW}Aktueller Status: {current_status}{Colors.RESET}")
    
    new_token = input(f"\n{Colors.YELLOW}Neuen GitHub Token eingeben (oder Enter zum Abbrechen): {Colors.RESET}").strip()
    
    if new_token:
        GITHUB_TOKEN = new_token
        HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        print(f"\n{Colors.GREEN}✅ Token aktualisiert!{Colors.RESET}")
        print(f"{Colors.YELLOW}⚠️  Hinweis: Token wird nur für diese Session gespeichert.{Colors.RESET}")
        print(f"{Colors.YELLOW}   Für permanente Speicherung bitte im Skript eintragen.{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}Token-Konfiguration abgebrochen.{Colors.RESET}")
    
    input(f"\n{Colors.CYAN}Drücke Enter um fortzufahren...{Colors.RESET}")

def exit_program():
    """Programm beenden"""
    print(f"\n{Colors.BOLD}{Colors.RED}🚪 PROGRAMM BEENDEN{Colors.RESET}")
    print(f"{Colors.GREEN}Auf Wiedersehen! 👋{Colors.RESET}")
    print(f"{Colors.CYAN}Danke für die Nutzung des RepoManagers!{Colors.RESET}")
    sys.exit(0)

# Aktionen-Dictionary
ACTIONS = {
    "A": ("ConstructionKit Versionen prüfen", check_constructionkit_versions),
    "B": ("Config.json erstellen/bearbeiten", create_edit_config),
    "C": ("ConstructionKit Versionen updaten", update_constructionkit_versions),
    "D": ("Letzte Ergebnisse anzeigen", show_last_results),
    "E": ("GitHub Token konfigurieren", configure_github_token),
    "F": ("Exit", exit_program),
}

def get_user_choice():
    """Benutzereingabe mit Farbunterstützung"""
    while True:
        choice = input(f"\n{Colors.BOLD}{Colors.WHITE}Bitte Auswahl eingeben: {Colors.RESET}").strip().upper()
        
        if choice in ACTIONS:
            return choice
        else:
            print(f"{Colors.RED}❌ Ungültige Auswahl!{Colors.RESET}")
            print(f"{Colors.YELLOW}Bitte A, B, C, D, E oder F eingeben.{Colors.RESET}")

def main() -> None:
    """Hauptfunktion"""
    try:
        while True:
            clear_screen()
            print_banner()
            print_menu()
            
            choice = get_user_choice()
            _, func = ACTIONS[choice]
            
            clear_screen()
            func()
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Programm wurde durch Benutzer abgebrochen.{Colors.RESET}")
        print(f"{Colors.GREEN}Auf Wiedersehen! 👋{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Ein Fehler ist aufgetreten: {e}{Colors.RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
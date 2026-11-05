#!/usr/bin/env python3
"""PreToolUse del technical-leader: lee todo, escribe solo en scratch/planes/.

Lista negra: Bash se bloquea solo si algo del comando escribe o ejecuta cosas (exit 2, el motivo va por stderr); lo demás pasa.
Write y Edit se permiten solo bajo scratch/planes/. Permiso de lectura de código; no es una defensa contra un atacante.
"""
import json
import os
import re
import shlex
import sys

PROHIBIDOS = {"rm", "mv", "cp", "touch", "tee", "mkdir", "rmdir", "chmod", "chown", "ln", "dd", "truncate", "install",
              "sudo", "su", "systemctl", "service", "kill", "pkill", "killall", "reboot", "shutdown", "apt", "apt-get",
              "pip", "pip3", "npm", "npx", "pnpm", "yarn", "wget", "scp", "rsync", "ssh", "psql", "alembic", "nvidia-smi",
              "node", "perl", "ruby", "bash", "sh", "zsh", "eval", "exec", "source", "nohup", "env"}
GIT = {"log", "show", "diff", "status", "blame", "grep", "ls-files", "rev-parse", "branch", "tag", "describe",
       "shortlog", "cat-file", "ls-tree", "stash"}
GIT_STASH = {"list", "show"}
DOCKER = {"ps", "logs", "inspect", "images", "stats", "top", "port", "version", "info", "compose"}
DOCKER_COMPOSE = {"ps", "logs", "config", "images", "top", "version"}
MAKE = {"test", "calls-active", "dev-health", "dev-ps", "dev-logs", "dev-login", "deploy-status", "llm-lb-status",
        "monitoring-status", "help", "migrate-test"}
CURL_ESCRIBE = ("-X", "--request", "-d", "--data", "--data-binary", "--data-raw", "--data-urlencode", "-F", "--form",
                "-T", "--upload-file", "-o", "--output", "-O", "--remote-name")
PYTHON_ESCRIBE = ("open(", "write", "os.", "subprocess", "shutil", "pathlib", "import socket", "urllib.request.urlopen(",
                  "__import__", "sys.modules")
XARGS = {"grep", "rg", "cat", "head", "tail", "wc", "ls", "stat", "file"}
FIND_PROHIBIDO = ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls")
SEPARADORES = set(";|&()")


def motivo(comando: str) -> str | None:
    if not comando.strip():
        return "comando vacío"
    if "`" in comando or "$(" in comando or "<(" in comando or ">(" in comando:
        return "sin sustitución de comandos: separá en dos pasos"
    # Las redirecciones que no escriben nada se permiten; cualquier otra, no.
    limpio = re.sub(r"(&|\d)?>{1,2}\s*/dev/null(?=$|[\s;|&)])|\d>&\d", " ", comando)
    lex = shlex.shlex(limpio, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    tokens = list(lex)
    segmento: list[str] = []
    for token in tokens + [";"]:
        if token and ">" in token and set(token) <= set("<>&|;()"):
            return "sin redirecciones a archivos"
        if token and set(token) <= SEPARADORES:
            if segmento and (error := revisar(segmento)):
                return error
            segmento = []
        else:
            segmento.append(token)
    return None


def revisar(segmento: list[str]) -> str | None:
    # Variables al frente (FOO=1 cmd) se ignoran; una asignación sola no hace nada.
    while segmento and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", segmento[0]):
        segmento = segmento[1:]
    if not segmento:
        return None
    cmd, args = os.path.basename(segmento[0]), segmento[1:]
    if cmd in PROHIBIDOS:
        return f"«{cmd}» escribe, ejecuta o toca otro host"
    if cmd in ("python", "python3"):
        codigo = " ".join(a for a in args if not a.startswith("-"))
        if "-c" not in args or any(p in codigo for p in PYTHON_ESCRIBE):
            return "python solo con -c y sin escribir, ejecutar ni red"
    elif cmd == "sed":
        if any(a in ("-i", "--in-place") or a.startswith("-i") for a in args):
            return "sed sin -i"
        for a in (x for x in args if not x.startswith("-")):
            # Sin el contenido de s/// e y/// ni las direcciones /re/, un w, W o e que quede al frente de un comando escribe o ejecuta.
            limpio = re.sub(r"[sy](.)(?:\\.|(?!\1).)*\1(?:\\.|(?!\1).)*\1[a-zA-Z0-9]*", "s", a)
            limpio = re.sub(r"/(?:\\.|[^/])*/", "/", limpio)
            if re.search(r"(^|[;{\n])\s*[0-9$,/~+!\s]*[wWe](\s|$)", limpio):
                return "sed sin los comandos w ni e"
    elif cmd in ("awk", "gawk", "mawk"):
        if any("system(" in a or ">" in a or "|" in a for a in args):
            return "awk sin system(), redirecciones ni tuberías"
    elif cmd == "git":
        while args and (args[0] in ("--no-pager", "-P") or args[0].startswith("--git-dir") or args[0].startswith("--work-tree")):
            args = args[1:]
        while len(args) >= 2 and args[0] in ("-C", "-c"):
            args = args[2:]
        if not args or args[0] not in GIT:
            return f"de git solo se permite: {', '.join(sorted(GIT))}"
        if args[0] == "stash" and (len(args) < 2 or args[1] not in GIT_STASH):
            return "de git stash solo list y show"
        if args[0] in ("branch", "tag") and any(a.startswith("-") and a not in ("-a", "-r", "-v", "-vv", "-l", "--list", "--contains", "--merged", "--no-merged") for a in args[1:]):
            return f"git {args[0]} solo para listar"
        if any(a in ("--output", "--ext-diff", "-O") or a.startswith("--output=") or a.startswith("-O") for a in args):
            return f"opción no permitida en git: salida a archivo"
    elif cmd == "docker":
        if not args or args[0] not in DOCKER:
            return f"de docker solo se permite: {', '.join(sorted(DOCKER))}"
        if args[0] == "compose":
            sub = [a for a in args[1:] if not a.startswith("-") and not a.endswith((".yml", ".yaml"))]
            if not sub or sub[0] not in DOCKER_COMPOSE:
                return f"de docker compose solo se permite: {', '.join(sorted(DOCKER_COMPOSE))}"
    elif cmd == "make":
        objetivos = [a for a in args if not a.startswith("-") and "=" not in a]
        if "-n" not in args and "--dry-run" not in args and not all(o in MAKE for o in objetivos):
            return f"de make solo se permite: {', '.join(sorted(MAKE))} (o make -n)"
    elif cmd == "curl":
        if any(a == p or a.startswith(p + "=") for a in args for p in CURL_ESCRIBE):
            return "curl solo GET y sin guardar a archivo"
    elif cmd in ("find", "bfs"):
        if any(a in FIND_PROHIBIDO for a in args):
            return f"{cmd} sin ejecutar ni borrar"
    elif cmd == "xargs":
        resto = [a for a in args if not a.startswith("-")]
        if not resto or os.path.basename(resto[0]) not in XARGS:
            return f"xargs solo con: {', '.join(sorted(XARGS))}"
    elif cmd == "crontab":
        if args != ["-l"]:
            return "crontab solo -l"
    elif cmd in ("sort", "rg") and any(a in ("-o", "--output", "--pre", "--compress-program") or a.startswith(("-o", "--output=", "--pre=")) for a in args):
        return f"opción de {cmd} que escribe o ejecuta"
    return None


def ruta_permitida(ruta: str) -> bool:
    raiz = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    real = os.path.realpath(ruta if os.path.isabs(ruta) else os.path.join(raiz, ruta))
    return real.startswith(os.path.join(raiz, "scratch", "planes") + os.sep)


try:
    entrada = json.load(sys.stdin)
    herramienta = entrada.get("tool_name", "Bash")
    if herramienta == "Bash":
        error = motivo(entrada["tool_input"]["command"])
    elif herramienta in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        ruta = entrada["tool_input"].get("file_path") or entrada["tool_input"].get("notebook_path") or ""
        error = None if ruta_permitida(ruta) else f"solo se escribe bajo scratch/planes/ (pediste {ruta})"
    else:
        error = None
except Exception as e:  # lo que no se puede analizar no se ejecuta
    error = f"no se pudo analizar el comando ({e})"
if error:
    print(f"Agente de solo lectura, bloqueado: {error}.", file=sys.stderr)
    sys.exit(2)

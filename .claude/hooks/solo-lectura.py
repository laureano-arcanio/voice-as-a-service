#!/usr/bin/env python3
"""PreToolUse de Bash para los agentes que no pueden modificar nada (technical-leader, validador).

Lista blanca: lo que no se reconoce como lectura se bloquea (exit 2, el motivo va por stderr).
Permiso de lectura de código; no es una defensa contra un atacante.
"""
import json
import re
import shlex
import sys

COMANDOS = {"cat", "head", "tail", "grep", "egrep", "rg", "find", "bfs", "ls", "wc", "sort", "cut", "tr",
            "diff", "stat", "du", "pwd", "echo", "basename", "dirname", "realpath", "jq", "cd", "nl", "column", "true"}
GIT = {"log", "show", "diff", "status", "blame", "grep", "ls-files", "rev-parse"}
OPCIONES_PROHIBIDAS = {
    "find": ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls"),
    "bfs": ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls"),
    "rg": ("--pre",),
    "sort": ("-o", "--output", "--compress-program"),
    "git": ("--output", "--ext-diff", "-O", "--open-files-in-pager", "--no-index"),
}
SEPARADORES = set(";|&()")


def motivo(comando: str) -> str | None:
    if not comando.strip():
        return "comando vacío"
    if "\n" in comando:
        return "una sola línea, sin saltos: separá con ; o &&"
    if "`" in comando or "$(" in comando or "<(" in comando or ">(" in comando:
        return "sin sustitución de comandos"
    # Las redirecciones que no escriben nada se permiten; cualquier otra, no.
    limpio = re.sub(r"(&|\d)?>\s*/dev/null(?=$|[\s;|&)])|\d>&\d", " ", comando)
    lex = shlex.shlex(limpio, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    lex.commenters = ""
    tokens = list(lex)
    segmento: list[str] = []
    for token in tokens + [";"]:
        if token and ">" in token and set(token) <= set("<>&|;()"):
            return "sin redirecciones de salida"
        if token and set(token) <= SEPARADORES:
            if segmento and (error := revisar(segmento)):
                return error
            segmento = []
        else:
            segmento.append(token)
    return None


def revisar(segmento: list[str]) -> str | None:
    cmd, args = segmento[0], segmento[1:]
    if cmd == "sed":
        # Solo imprimir un rango: sed puede editar (-i), escribir (w) y ejecutar (e).
        if len(args) >= 2 and args[0] == "-n" and re.fullmatch(r"\d*,?(\d+|\$)?p", args[1]):
            return None
        return "de sed solo se permite imprimir rangos: sed -n 'A,Bp' archivo"
    if cmd == "git":
        if not args or args[0] not in GIT:
            return f"de git solo se permite: {', '.join(sorted(GIT))}"
    elif cmd not in COMANDOS:
        return f"«{cmd}» no está en la lista de lectura"
    for arg in args:
        if any(arg == p or arg.startswith(p + "=") or (p in ("-o", "-O") and arg.startswith(p))
               for p in OPCIONES_PROHIBIDAS.get(cmd, ())):
            return f"opción no permitida en {cmd}: {arg}"
    return None


try:
    error = motivo(json.load(sys.stdin)["tool_input"]["command"])
except Exception as e:  # lo que no se puede analizar no se ejecuta
    error = f"no se pudo analizar el comando ({e})"
if error:
    print(f"Agente de solo lectura, comando bloqueado: {error}.", file=sys.stderr)
    sys.exit(2)

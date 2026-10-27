# Sandbox de las herramientas de codigo (docs/TOOLS_PLAN.md, 5). Deno fijado (2.8.3).
FROM denoland/deno:alpine-2.8.3
WORKDIR /app
COPY server.ts runner.js ./
RUN deno check server.ts
USER deno
EXPOSE 8080
# El servidor: escucha, lee sus variables, lanza `deno` (el mismo binario) y nada mas.
CMD ["deno", "run", "--allow-net=0.0.0.0:8080", "--allow-env=TOOLS_RUNNER_TOKEN,TOOLS_RUNNER_CONCURRENCY,TOOLS_EGRESS_PROXY", "--allow-run=/bin/deno", "--allow-read=/app", "server.ts"]

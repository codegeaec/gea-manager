# gea

`gea` prepara tu máquina y tus proyectos para programar con agentes de IA. Un
agente **planner** (por ejemplo Claude Code) planifica y revisa; uno o varios
**subagentes** (Codex, OpenCode, agy, Kimi…) implementan las tareas que les
delega. Todo se coordina con [herdr](https://herdr.dev) y con tasks en archivos
Markdown, así que cualquier agente puede retomar el trabajo sin depender del
historial del chat.

- **Máquina:** instala y configura herdr, las CLIs de agentes, rtk, codegraph,
  la CLI de shadcn y las herramientas de línea de comandos habituales.
- **Proyecto:** deja `AGENTS.md`, `.agents/`, `gea.json` y un flujo de trabajo
  (planificar → delegar → revisar → cerrar), tanto en proyectos nuevos como en
  los que ya están empezados.

## Contenido

- [Instalación](#instalación)
- [Inicio rápido](#inicio-rápido)
- [Configuración: `gea.json` y `gea.local.json`](#configuración-geajson-y-gealocaljson)
- [Agentes: planner y subagentes](#agentes-planner-y-subagentes)
- [El workspace: `gea` sin argumentos](#el-workspace-gea-sin-argumentos)
- [Tasks y delegación](#tasks-y-delegación)
- [Permisos, worktrees y panes de los builders](#permisos-worktrees-y-panes-de-los-builders)
- [Revisión y traspaso de orquestador](#revisión-y-traspaso-de-orquestador)
- [Seguridad y mantenimiento](#seguridad-y-mantenimiento)
- [Referencia de comandos](#referencia-de-comandos)
- [Desarrollo](#desarrollo)
- [Licencia](#licencia)

## Instalación

En Linux, macOS o WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/codegeaec/gea-manager/main/install.sh | bash
```

En Windows, desde PowerShell (instala WSL2 y Ubuntu si hace falta y ejecuta
`install.sh` dentro):

```powershell
irm https://raw.githubusercontent.com/codegeaec/gea-manager/main/install.ps1 | iex
```

## Inicio rápido

```bash
gea setup     # una vez por máquina: herramientas, CLIs de agentes, integraciones, skills
cd mi-proyecto
gea init      # una vez por proyecto (nuevo o ya empezado): pregunta idioma, agentes y modelos
gea           # abre el workspace de herdr del proyecto
gea doctor    # comprueba herramientas, sesión de cada agente y tamaño del contexto
```

`setup`, `init`, `skills sync` y `uninstall` aceptan `--dry-run`: cuentan qué
harían sin escribir ni instalar nada. `gea init --yes` acepta todos los valores
por defecto (idiomas con `--lang-agents`, `--lang-docs` y `--lang-commits`).

### Qué hace `gea init`

- Muestra primero un informe de lo que ya existe y nunca sobrescribe tus
  archivos: en un `AGENTS.md`, `CLAUDE.md` o `README.md` propios añade un bloque
  delimitado por `<!-- gea:start -->` y `<!-- gea:end -->`; lo que falta lo crea.
- Pregunta el idioma de los agentes (`AGENTS.md`, `.agents/`), de los documentos
  (`docs/`) y de los commits, cada uno por separado.
- Pregunta el planner, su modelo y los subagentes (los modelos se leen de cada
  CLI; ver [Agentes](#agentes-planner-y-subagentes)).
- Crea `.agents/gea.md` (chuleta de comandos), los comandos `/gea-plan`,
  `/gea-delegate` y `/gea-review` para Claude Code y OpenCode, y un hook
  pre-commit que busca secretos y vigila el tamaño de `AGENTS.md`.
- Si el proyecto tiene tasks en otro formato, ofrece importarlas
  (`gea task import`).

Un agente no necesita skills para trabajar con gea: `AGENTS.md` apunta a
`.agents/gea.md`, y `gea guide [plan|delegate|review|build]` imprime la guía
paso a paso en el idioma del proyecto.

## Configuración: `gea.json` y `gea.local.json`

| Archivo | Se commitea | Contenido |
|---|---|---|
| `gea.json` | Sí | Política del proyecto: `verify`, `tasks`, `tabs`, `builders`, `autonomy`, `lang`, `pm`. |
| `gea.local.json` | No (ignorado) | Tus elecciones personales: `agents` (planner, modelos y subagentes) y `builders.mode`. |

`gea.local.json` gana sobre `gea.json` al cargar. Ambos llevan `schema_version`;
un archivo con una versión más nueva que la que entiende tu gea se rechaza con
un error claro. Las tasks viven en `~/gea/projects/<proyecto>` (`tasks.location:
"home"`) o en `.gea/` dentro del repo (`"repo"`, versionado).

Ajustes útiles de `gea.json`:

| Clave | Valores | Efecto |
|---|---|---|
| `autonomy` | `supervised` · `balanced` · `autonomous` | Cuánta libertad tiene el builder (se lo dice a cada agente). |
| `verify` | lista de comandos | Lo que corre `gea verify` (por ejemplo `pnpm exec tsc --noEmit`). |
| `builders.close` | `on-success` (defecto) · `never` | Si se cierra el pane del builder al terminar una corrida verificada. |
| `builders.permissions` | `safe` (defecto) · `yolo` | Flags de permisos con que se abren los builders. |
| `builders.worktrees` | `true` · `false` | Delegar siempre en un worktree aislado. |

## Agentes: planner y subagentes

La clave `agents` guarda quién planifica y a quién se delega:

```json
{
  "agents": {
    "planner": "claude",
    "plannerModel": "opusplan",
    "subagents": [
      "codex",
      { "id": "oc-kimi", "model": "opencode-go/kimi-k2.7-code" },
      { "id": "oc-lite", "cli": "opencode", "model": "opencode-go/deepseek-v4-flash" }
    ]
  }
}
```

- **`planner`:** `claude`, `codex`, `opencode`, `agy` o `kimi` (por defecto
  `claude`). **`plannerModel`** es opcional: en Claude se aplica con `/model` al
  crear el tab; en las demás CLIs, con su flag `--model` al arrancar.
- **`subagents`:** el orden de la lista es la prioridad de delegación. Cada
  entrada puede ser:
  - un **id** de un perfil detectado en tu máquina (`codex`, `oc-kimi`…);
  - un objeto con ese **id y un `model`**, que cambia el modelo del perfil
    detectado (override);
  - un objeto con **`cli`**, que define un subagente nuevo: por ejemplo otro
    OpenCode con otro modelo. Necesita un `id` único (`[a-z][a-z0-9_-]*`).
- Sin lista de subagentes se usan todos los perfiles detectados.

**Pool de cupo:** los modelos de una misma cuenta comparten cupo. Cada subagente
tiene un `pool` opcional; si no lo indicas, gea usa el proveedor del modelo
(`opencode-go/…` → `opencode-go`) o el nombre de la CLI, y para agy la familia
del modelo. Cuando un builder agota su cupo, se marca todo su pool, y por eso
dos subagentes de la misma cuenta deben compartirlo.

### Gestionar los agentes sin editar JSON

```bash
gea agents manage                  # menú interactivo: planner, añadir, cambiar modelo, quitar, prioridad
gea agents planner codex --model gpt-5.5
gea agents add oc-lite --cli opencode --model opencode-go/deepseek-v4-flash
gea agents add codex               # añade un perfil detectado
gea agents remove oc-lite
gea agents models [cli]            # modelos que reporta cada CLI
gea agents list                    # planner y subagentes resueltos (⚠ si un modelo ya no existe)
gea agents refresh                 # vuelve a detectar las CLIs instaladas
```

`gea agents manage` escribe la clave `agents` en `gea.local.json`, así que no
hace falta conocer el esquema. Los modelos no se escriben a mano: se eligen de
la lista real de cada CLI (`opencode models`, `agy models`, `codex debug
models`; Claude usa sus alias `opusplan`, `opus`, `sonnet` y `haiku`, y Kimi
pide el nombre). Cambiar el planner afecta al próximo tab que gea cree; no
reinicia el que ya está abierto.

Los proyectos anteriores, con `primary`, `primaryModel` y `builders.allow`, se
leen igual y se migran solos al guardar.

## El workspace: `gea` sin argumentos

`gea` abre (o enfoca) el workspace de herdr del proyecto con estos tabs:

1. El planner (`claude` por defecto), ya iniciado. En un workspace nuevo
   reutiliza el tab con el que herdr lo crea, de modo que no queda un tab `1`
   suelto.
2. `terminal`, un shell en la raíz del repo.
3. Los tabs extra que declares en `tabs`.

Es idempotente por nombre de tab: volver a correr `gea` no duplica nada y solo
crea lo que falta. Los agentes reciben nombres `<3 letras del proyecto>-<rol>`
(`cot-claude`, `cot-builder-codex`) para que dos proyectos abiertos a la vez no
choquen; si el nombre ya existe en otro workspace se añade `-2`, `-3`…

### Tabs adicionales (monorepos)

```json
{
  "tabs": [
    { "label": "web", "cwd": "apps/web" },
    { "label": "api", "cwd": "apps/api", "command": "pnpm dev" },
    { "label": "docs", "cwd": "packages/docs" }
  ]
}
```

| Campo | Obligatorio | Qué hace |
|---|---|---|
| `label` | Sí | Nombre del tab. Único (sin distinguir mayúsculas) y distinto de `terminal` y del planner. |
| `cwd` | No | Carpeta del shell, **relativa a la raíz del repo** (sin rutas absolutas ni `..`). Por defecto, la raíz. Si no existe, gea avisa y omite ese tab. |
| `command` | No | Comando que se ejecuta **solo cuando gea crea el tab**; al reabrir no se relanza, así que un `pnpm dev` no se reinicia. |

Los tabs van en el orden del JSON, después del planner y de `terminal`. Para
tener tabs propios, ponlos en `gea.local.json`: una lista `tabs` ahí reemplaza a
la compartida. Si ya tienes un workspace abierto, gea no cierra ni renombra tabs
que no creó; solo añade los que faltan.

## Tasks y delegación

Los cambios no triviales pasan por una task, un archivo Markdown con objetivo,
plan, `## Files` (qué rutas puede tocar el builder) y `## Acceptance` (criterios
comprobables). El planner la escribe; el builder solo la implementa.

```bash
gea task new "Título" --type bugfix    # bugfix | feature | refactor | spike
gea task new --from-issue 42           # arranca desde un issue de GitHub
gea task import                        # convierte tasks de otro formato a la estructura gea
gea delegate TASK-001                  # checkpoint de git + builder + resumen de 5 líneas
gea verify --task TASK-001             # checks del proyecto + criterios de la task
gea undo TASK-001                      # vuelve al checkpoint previo a delegar
gea task done TASK-001                 # cierra; su ## Decisions pasa a docs/decisions.md
gea pr TASK-001                        # abre el PR desde la task (pide confirmación)
gea status                             # tasks activas, panes y pools agotados
```

Cabeceras opcionales de la task: `Tier: S|M|L` (gea reparte por dificultad y, con
historial, por tasa de éxito) y `Budget: 45m` (tiempo máximo del builder; 30
minutos por defecto).

Lo que gea hace por ti al delegar:

- **Aviso de alcance:** avisa de los archivos tocados fuera de `## Files`, y de
  una task sin `## Files` o `## Acceptance` completos.
- **Cupo agotado:** si el builder se detiene por un mensaje de cupo o rate
  limit, marca su pool como no disponible hasta el reinicio, cierra el pane y te
  dice a qué agente probar.
- **`gea verify` sin colgarse:** imprime `→ comando` y un latido cada pocos
  segundos, mata todo el árbol de procesos si lo interrumpen y solo permite una
  ejecución a la vez por repo.
- **Registro:** cada intento queda en `~/gea/delegations.jsonl`;
  `gea agents stats` resume éxito y duración por agente y tier.

## Permisos, worktrees y panes de los builders

Un builder que se detiene a pedir permiso deja la delegación en `BLOCKED`:
herdr no puede responder esos diálogos por script. `builders.permissions`
decide con qué flags se abre cada builder (nunca el tab del planner):

| Valor | Qué hace | Flags por CLI |
|---|---|---|
| `safe` (defecto) | Lo más desatendido que cada CLI permite sin perder límites | claude `--permission-mode acceptEdits` · codex `--sandbox workspace-write --ask-for-approval never` · opencode ninguno (rigen las reglas de `opencode.jsonc`) · agy `--mode accept-edits` |
| `yolo` | Sin ninguna verificación de permisos | claude `--dangerously-skip-permissions` · codex `--dangerously-bypass-approvals-and-sandbox` · opencode `--auto` · agy `--dangerously-skip-permissions` |

Kimi no recibe flags (no están verificados). **`yolo` solo se permite dentro de
un worktree:** sin `--worktree` (o `builders.worktrees: true`), `gea delegate`
se niega antes de abrir nada. `gea review` y `gea agents start` nunca usan
`yolo`. Aun así, un builder en `yolo` puede ejecutar cualquier comando, incluida
la red o `git push`: el worktree protege tu árbol de trabajo, no tu cuenta.

### Worktrees con dependencias

Un worktree nuevo no trae `node_modules` ni archivos ignorados como `.env`:

```json
{
  "builders": {
    "permissions": "yolo",
    "worktrees": true,
    "worktree": {
      "copy": [".env"],
      "setup": "pnpm install --frozen-lockfile && pnpm prisma:generate"
    }
  }
}
```

- `copy`: archivos, con ruta relativa al repo, que se copian al worktree si
  existen. Nunca entran en el commit del builder ni en su lista de archivos
  tocados.
- `setup`: comando que se ejecuta dentro del worktree al crearlo (máximo 15
  minutos). Si falla, el worktree se elimina y la delegación se cancela con el
  error.

### Cierre de panes

Tras una corrida verificada, gea cierra el pane que abrió para el builder
(`builders.close: "on-success"`, por defecto). Las corridas fallidas, bloqueadas
o con timeout quedan abiertas para que las inspecciones. Una ronda de corrección
sobre una task cuyo pane se cerró empieza con sesión nueva; el archivo de la task
lleva el contexto. Con `"never"` se conservan todos los panes y sus sesiones.
gea no cierra nunca un pane que abriste tú, ni el del propio orquestador.

## Revisión y traspaso de orquestador

```bash
gea review-pack TASK-001      # task + diff acotado + verify + avisos en un solo archivo
gea review TASK-001           # revisa un modelo distinto al que implementó
gea handoff --to codex        # escribe HANDOFF.md y arranca otro orquestador con él
```

`gea handoff` genera un prompt de retoma desde lo que está en curso (tasks en
progreso o en revisión, estado de git, checkpoints y pools agotados) y, con
`--to`, arranca el nuevo orquestador en un pane y ofrece fijarlo como planner.

## Seguridad y mantenimiento

```bash
gea scan-secrets   # busca secretos en el diff staged; init lo instala como hook pre-commit
gea lint           # avisa si AGENTS.md, CLAUDE.md o una skill pesan demasiado
gea skills prune   # ofrece quitar skills que gea no instaló (cada una cuesta tokens)
gea update         # actualiza herramientas, instrucciones globales y skills
gea uninstall      # revierte lo que setup registró, con backup y confirmación
```

## Referencia de comandos

| Comando | Para qué sirve |
|---|---|
| `gea setup` · `gea update` · `gea uninstall` | Preparar, actualizar y revertir la máquina |
| `gea doctor` · `gea lint` | Diagnóstico de herramientas, sesiones de agentes y contexto |
| `gea init` | Preparar un proyecto |
| `gea` | Abrir el workspace de herdr |
| `gea agents manage \| planner \| add \| remove \| models \| list \| refresh \| stats` | Agentes, modelos y estadísticas |
| `gea task new \| list \| show \| status \| done \| import` · `gea subtask new` | Tasks y subtasks |
| `gea delegate` · `gea undo` · `gea verify` | Delegar, deshacer y comprobar |
| `gea review-pack` · `gea review` · `gea handoff` · `gea pr` | Revisar, traspasar y publicar |
| `gea status` | Estado de tasks, panes y pools |
| `gea guide [plan\|delegate\|review\|build]` | Guía paso a paso para agentes |
| `gea scan-secrets` · `gea skills sync \| list \| prune` | Seguridad y skills |

Más detalle en `docs/` (diseño de cada parte) y `docs/commands.md` (comportamiento
de cada comando).

## Desarrollo

```bash
uv sync --group dev
uv run pytest
uv run ruff check .
```

Las reglas del repositorio están en `AGENTS.md`.

## Licencia

[MIT](LICENSE)

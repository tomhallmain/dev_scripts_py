A mapping of the original `dev_scripts` commands (below) to the ported commands in this
project, plus the remaining work needed before the port is complete enough to build.

Status as of 2026-11-21, reconciled against `scripts/cli.py` (not against earlier versions of
this file) and against the original project's commit history through 2026-09-21. The command
table below is the original `ds:commands` listing, extended with the five commands the
original gained after this file was first written (`ds:copy`, `ds:kill_port`, `ds:move`,
`ds:parallel`, `ds:retry`).

```log
    COMMAND              ALIAS    DESCRIPTION                                      USAGE

**  ds:agg                        Aggregate by index/pattern                       ds:agg [-h|file*] [r_aggs=+] [c_aggs=+]
    ds:asgn                       Print lines matching assignment pattern          ds:asgn file
**  ds:case                       Recase text data globally or in part             ds:case [string] [tocase=proper] [filter]
    ds:cd                         cd to higher or lower level dirs                 ds:cd [search]
**  ds:color                      Get RGB from hex or hex from RGB                 ds:color [hex|rgb|r] [g] [b]
    ds:commands                   List dev_scripts commands                        ds:commands [bufferchar] [utils] [re_source]
**  ds:comps                      Get non-matching lines from two datasets         ds:comps file [file] [awkargs]
    ds:copy                       Copy files/dirs, optionally filtered by [tag]    ds:copy source target [filter]
**  ds:cp                         Copy standard input in UTF-8                     data | ds:cp
**  ds:decap                      Remove up to n_lines from the start of a file    ds:decap [file] [n_lines=1]
    ds:deps                       Identify dependencies of a shell function        ds:deps name [filter] [ntype=FUNC|ALIAS] [caller] [ndata]
    ds:deps2                      Identify dependencies of C, Java functions       ds:deps2 file
**  ds:diff                       Diff shortcut for an easier to read view         ds:diff file1|str1 [file2|str2] [suppress_common] [color=t]
**  ds:diff_fields       ds:df    Get elementwise diff of two datasets             ds:df file [file*] [op=-] [exc_fields=0] [prefield=f] [awkargs]
**  ds:dostounix                  Remove ^M / CR characters in place               ds:dostounix [file*]
**  ds:dup_input                  Duplicate standard input in aggregate            data | ds:dup_input
    ds:dups                       Report duplicate files with option for deletion  ds:dups [dir] [confirm=f] [of_file] [try_nonmatch_ext=f]
**  ds:embrace                    Enclose a string on each side by args            ds:embrace [str] [left={] [right=}]
    ds:enti                       Print text entities separated by pattern         ds:enti [file] [sep= ] [min=1] [order=a]
    ds:fail                       Safe failure that kills parent                   ds:fail [error_message]
**  ds:field_replace              Overwrite field val if matches pattern           ds:field_replace [file] val_replace_func [key=1] [pattern=]
**  ds:fieldcounts       ds:fc    Print value counts                               ds:fc [file] [fields=1] [min=1] [order=a] [awkargs]
    ds:filename_str               Add string to filename, preserving path          ds:filename_str file str [prepend|append|replace] [abs_path=t]
**  ds:fit                        Fit fielded data in columns with dynamic width   ds:fit [-h|file*] [prefield=t] [awkargs]
    ds:fsrc                       Show the source of a shell function              ds:fsrc func
    ds:gexec                      Generate script from parts of another and run    ds:gexec run=f srcfile outputdir reo_r_args [clean] [verbose]
    ds:git_add_com_push  ds:gacp  Add, commit with message, push                   ds:gacp commit_message [prompt=t]
    ds:git_branch        ds:gb    Run git branch for all repos                     ds:gb
    ds:git_branch_refs   ds:gbr   List branches merged to a branch                 ds:git_branch_refs [branch=develop] [invert=f]
    ds:git_checkout      ds:gco   Checkout branch matching pattern                 ds:gco [branch_pattern] [new_branch=f]
    ds:git_cross_view    ds:gcv   Display table of git repos vs branches           ds:gcv [:ab:Dfhmo:sv]
    ds:git_diff                   Diff shortcut for exclusions                     ds:git_diff obj obj exclusions
    ds:git_graph         ds:gg    Print colorful git history graph                 ds:gg
    ds:git_purge_local   ds:gpl   Purge branches from local git repos              ds:gpl [repos_dir=~]
    ds:git_recent        ds:gr    Display commits sorted by recency                ds:gr [refs=heads] [run_context=display]
    ds:git_recent_all    ds:gra   Display recent commits for local repos           ds:gra [refs=heads] [repos_dir=~]
    ds:git_refresh       ds:grf   Pull latest for all repos, run installs          ds:grf [repos_dir=~]
    ds:git_squash        ds:gsq   Squash last n commits                            ds:gsq [n_commits=1]
    ds:git_status        ds:gs    Run git status for all repos                     ds:gs
    ds:git_time_stat     ds:gts   Last local pull+change+commit times              cd repo; ds:gts
    ds:git_word_diff     ds:gwdf  Git word diff shortcut                           ds:gwdf [git_diff_args]
    ds:goog                       Search Google                                    ds:goog [search query]
**  ds:graph                      Extract graph relationships from DAG base data   ds:graph [file]
    ds:grepvi            ds:gvi   Grep and open vim on match                       ds:gvi search [file|dir] [edit_all_match=f]
    ds:help                       Print help for a given command                   ds:help ds_command
**  ds:hist                       Print histograms for all number fields in data   ds:hist [file] [n_bins] [bar_len] [awkargs]
**  ds:index             ds:i     Attach an index to lines from a file or STDIN    ds:i [file] [startline=1]
    ds:inferfs                    Infer field separator from data                  ds:inferfs file [reparse=f] [custom=t] [file_ext=t] [high_cert=f]
    ds:inferh                     Infer if headers present in a file               ds:inferh file [awkargs]
    ds:inferk                     Infer join fields in two text data files         ds:inferk file1 file2 [awkargs]
**  ds:insert                     Redirect input into a file at lineno or pattern  ds:insert file [lineno|pattern] [srcfile] [inplace=f]
    ds:iter                       Repeat a string                                  ds:iter str [n=1] [fs]
    ds:jira                       Open Jira at specified workspace issue / search  ds:jira workspace_subdomain [issue|query]
**  ds:join              ds:jn    Join two datasets with any keyset                ds:join file [file*] [jointype] [k|merge] [k2] [prefield=f] [awkargs]
**  ds:join_by                    Join a shell array by given delimiter            ds:join_by delimiter [join_array]
    ds:kill_port         ds:kp    Kill the process on a port or matching pattern   ds:kp port|pattern
**  ds:line                       Execute commands on var line                     ds:line [seed_cmds] line_cmds [IFS=\n]
**  ds:matches                    Get match lines from two datasets                ds:matches file [file] [awkargs]
**  ds:mini                       Crude minify, remove whitespace and newlines     ds:mini [file*] [newline_sep=;] [blank_only=f]
    ds:move              ds:mv    Move files/dirs, optionally filtered by [tag]    ds:mv source target [filter]
    ds:new                        Refresh zsh or bash interactive session          ds:new
**  ds:newfs                      Convert field separators - i.e. tsv -> csv       ds:newfs [file] [newfs=,] [awkargs]
    ds:nset                       Test name (function/alias/variable) is defined   ds:nset name [search_vars=f]
    ds:ntype                      Get name type - function, alias, variable        ds:ntype name
**  ds:parallel                   Run a command over piped items n at a time       data | ds:parallel [jobs=4] command [args]
    ds:path_elements              Return dirname/filename/extension from filepath  read -r dirpath filename extension <<< "$(ds:path_elements file)"
**  ds:pipe_check                 Detect if pipe has data or over [n_lines]        data | ds:pipe_check [n_lines]
**  ds:pivot                      Pivot tabular data                               ds:pivot [file] [y_keys] [x_keys] [z_keys=count_xy] [agg_type]
    ds:plot                       Get a scatter plot of from two fields            ds:plot [file] [field_y=1] [field_x=index]
**  ds:pow                        Combinatorial frequency of data field values     ds:pow [file] [min] [return_fields=f] [invert=f] [awkargs]
**  ds:prod                       Return product multiset of filelines             ds:prod file [file*] [awkargs]
**  ds:random                     Generate a random number 0-1 or randomize text   ds:random [number|text]
    ds:recent                     List files modified recently                     ds:recent [dir=.] [days=7] [recurse=f] [hidden=f] [only_files=f]
**  ds:reo                        Reorder/repeat/slice data by rows and cols       ds:reo [-h|file*] [rows] [cols] [prefield=t] [awkargs]
    ds:retry                      Retry a command with exponential backoff         ds:retry [attempts=3] [delay=1] command [args]
**  ds:rev                        Reverse lines from standard input                data | ds:rev
    ds:searchn                    Search shell environment names                   ds:searchn name
    ds:searchx                    Search for a C-lang/curly-brace object           ds:searchx file|dir [search] [q] [multilevel]
    ds:sedi                       Run global in place substitutions                ds:sedi file|dir search [replace]
**  ds:select                     Select code by regex anchors                     ds:select file [startpattern endpattern]
**  ds:shape                      Print data shape by length or pattern            ds:shape [-h|file*] [patterns] [fields] [chart_size=15ln] [awkargs]
    ds:so                         Search Stack Overflow                            ds:so [search_query]
**  ds:sort                       Sort with inferred field sep of 1 char           ds:sort [unix_sort_args] [file]
**  ds:sortm             ds:s     Sort with inferred field sep of >=1 char         ds:sortm [file] [keys] [order=a|d] [sort_type] [awkargs]
**  ds:space                      Modify file space or tab counts                  ds:space [file] from=$'\t' target=4
    ds:src                        Source a piece of shell code                     ds:src file ["searchx" pattern] || [start end] || [search linesafter]
    ds:srg                        Scope grep to files that contain a match         ds:srg scope_pattern search_pattern [dir] [invert=]
**  ds:stagger                    Print tabular data in staggered rows             ds:stagger [file] [stag_size]
**  ds:subsep                     Extend fields by a common subseparator           ds:subsep [-h|file] subsep_pattern [nomatch_handler= ]
**  ds:substr                     Extract a substring with regex                   ds:substr str [leftanc] [rightanc]
**  ds:test                       Test input quietly with extended regex           ds:test regex [str|file] [test_file=f]
    ds:tmp                        Shortcut for quiet mktemp                        ds:tmp filename
    ds:todo                       List todo items found in paths                   ds:todo [searchpaths=.]
    ds:trace                      Search shell trace for a pattern                 ds:trace [command] [search] [strace] [strace_args]
**  ds:transpose         ds:t     Transpose field values                           ds:transpose [file*] [prefield=t] [awkargs]
**  ds:unicode                    Get UTF-8 unicode for a character sequence       ds:unicode [str] [out=codepoint|hex|octet]
**  ds:uniq              ds:u     Get unique values >= min                         ds:u [file] [fields=1] [min=1] [order=a]
    ds:vi                         Search for files and open in vim                 ds:vi search [dir] [edit_all_match=f]
    ds:websel                     Download and extract inner html by regex         ds:websel url [tag_re] [attrs_re]

    COMMAND              ALIAS    DESCRIPTION                                      USAGE

** - function supports receiving piped data```


## Mapping

Status key:

- ✅ = wired, no WIP/STUB marker
- ✅* = completed on 2026-11-21 in the agent sandbox: the implementation modules were run against
  the original's reference cases, but `click`/`pytest` are not available there, so the pytest
  files have not been run yet (see [Conventions](#conventions-for-completing-the-port))
- WIP = wired, prints a work-in-progress warning (`@wip` in `scripts/cli.py`)
- STUB = wired, prints a stub warning and is hidden from `ds commands` unless `--all` is passed (`@stub`)
- script only = Python file exists but is not wired to the CLI
- — = not ported
- — (shell) = not ported; the original reads or changes the state of the calling shell session, which a standalone process cannot do (see [Not ported](#not-ported))

The Tests column names the pytest file that exercises the command, either through the CLI or
through its implementation module. "none" means no test covers the command. "Parity gap" in
Notes means the original changed after the command was ported (see [Parity gaps](#parity-gaps)).

| Original             | dev_scripts_py     | Status      | Tests | Notes |
| -------------------- | ------------------ | ----------- | ----- | ----- |
| ds:agg               | `ds agg`           | ✅*         | `test_agg.py` | Range expressions only (see [Completed ports](#completed-ports)) |
| ds:asgn              | `ds asgn`          | ✅*         | `test_asgn_enti.py` | `lineno:line` for assignment lines; FILE or stdin |
| ds:case              | `ds case`          | ✅          | `test_case.py` | Parity gap: dash case |
| ds:cd                | `ds cd`            | ✅          | `test_cd_command.py` | Prints the resolved path for `cd "$(ds . cd <search>)"` |
| ds:color             |                    | —           | | |
| ds:commands          | `ds commands`      | ✅          | | Also available via `ds --help` |
| ds:comps             | `ds comps`         | ✅          | `test_matches.py` | Complement of `ds matches` |
| ds:copy              | `ds copy`          | ✅          | `test_move.py` | |
| ds:cp                | `ds cp`            | ✅          | `test_simple_commands.py` | Clipboard (UTF-8). macOS `pbcopy`, Windows PowerShell, Linux xclip/wl-copy/xsel |
| ds:decap             | `ds decap`         | ✅          | `test_simple_commands.py` | |
| ds:deps              |                    | — (shell)   | | |
| ds:deps2             |                    | —           | | |
| ds:diff              | `ds diff`          | ✅*         | `test_diff.py` | Side-by-side `difflib` diff, no external `diff` needed |
| ds:diff_fields       | `ds diff_fields` / `ds df` | ✅* | `test_diff_fields.py` | |
| ds:dostounix         | `ds dostounix`     | ✅          | `test_simple_commands.py` | In place for files; stdin to stdout |
| ds:dup_input         |                    | —           | | |
| ds:dups              | `ds dup_files`     | ✅          | `test_dup_files.py` | |
| ds:embrace           | `ds embrace`       | ✅          | `test_simple_commands.py` | |
| ds:enti              | `ds enti`          | ✅*         | `test_asgn_enti.py` | |
| ds:fail              |                    | — (shell)   | | |
| ds:field_replace     | `ds field_replace` | ✅          | `test_field_replace.py` | |
| ds:fieldcounts       | `ds field_counts`  | ✅          | `test_fieldcounts_uniq.py` | |
| ds:filename_str      | `ds filename_str`  | ✅          | `test_simple_commands.py` | |
| ds:fit               | `ds fit`           | ✅*         | `test_fit.py` | |
| ds:fsrc              |                    | — (shell)   | | |
| ds:gexec             |                    | —           | | |
| ds:git_add_com_push  | `ds git_add_com_push` / `ds gacp` | ✅ | `test_git_commands.py` | |
| ds:git_branch        | `ds git_branch` / `ds gb` | ✅  | `test_git_commands.py` | |
| ds:git_branch_refs   | `ds git_branch_refs` / `ds gbr` | ✅ | `test_git_commands.py` | |
| ds:git_checkout      | `ds git_checkout` / `ds gco` | ✅ | `test_git_commands.py` | |
| ds:git_cross_view    | `ds git_cross_view` / `ds gcv` | ✅ | `test_git_commands.py` | |
| ds:git_diff          | `ds git_diff`      | ✅          | `test_git_commands.py` | |
| ds:git_graph         | `ds git_graph` / `ds gg` | ✅   | `test_git_commands.py` | |
| ds:git_purge_local   | `ds git_purge_local` / `ds gpl` | ✅ | `test_git_commands.py` | Parity gap |
| ds:git_recent        | `ds git_recent` / `ds gr` | ✅  | `test_git_commands.py` | |
| ds:git_recent_all    | `ds git_recent_all` / `ds gra` | ✅ | `test_git_commands.py` | |
| ds:git_refresh       | `ds git_refresh` / `ds grf` | ✅ | `test_git_commands.py` | |
| ds:git_squash        | `ds git_squash` / `ds gsq` | ✅ | `test_git_commands.py` | |
| ds:git_status        | `ds git_status` / `ds gs` | ✅  | `test_git_commands.py` | |
| ds:git_time_stat     | `ds git_time_stat` / `ds gts` | ✅ | `test_git_commands.py` | |
| ds:git_word_diff     | `ds git_word_diff` / `ds gwdf` | ✅ | `test_git_commands.py` | |
| ds:goog              | `ds goog`          | ✅          | `test_simple_commands.py` | Opens browser search URL |
| ds:graph             | `ds graph`         | ✅*         | `test_graph.py` | Also detects indirect cycles |
| ds:grepvi            | `ds grepvi` / `ds gvi` | ✅      | `test_grep_edit.py` | Grep content and open in `$EDITOR` |
| ds:help              | `ds --help`        | ✅          | | Also `ds commands` |
| ds:hist              | `ds hist`          | ✅*         | `test_hist.py` | |
| ds:index             | `ds index`         | ✅          | `test_simple_commands.py` | |
| ds:inferfs           | `ds inferfs`       | ✅          | none | |
| ds:inferh            | `ds inferh`        | ✅*         | `test_inferh.py` | Exit code 0 = header row |
| ds:inferk            | `ds inferk`        | ✅*         | `test_inferk.py` | Simplified heuristic, as in `dsr` |
| ds:insert            | `ds insert`        | ✅          | `test_simple_commands.py` | |
| ds:iter              | `ds iter`          | ✅          | `test_simple_commands.py` | |
| ds:jira              | `ds jira`          | ✅          | `test_simple_commands.py` | Opens Jira workspace/issue/search URL |
| ds:join              | `ds join` / `ds jn` | ✅         | `test_join.py` | |
| ds:join_by           | `ds join_by`       | ✅          | `test_simple_commands.py` | |
| ds:kill_port         | `ds kill_port`     | ✅          | none | |
| ds:line              | `ds line`          | ✅          | `test_simple_commands.py` | Supports `{line}` placeholder in command |
| ds:matches           | `ds matches`       | ✅          | `test_matches.py` | Two paths or one path + stdin. `-k` / `--key1` / `--key2`, `--verbose` |
| ds:mini              |                    | —           | | |
| ds:move              | `ds move`          | ✅          | `test_move.py` | |
| ds:new               |                    | — (shell)   | | |
| ds:newfs             | `ds newfs`         | ✅          | `test_simple_commands.py` | |
| ds:nset              |                    | — (shell)   | | See `tool_availability` for the PATH-probe part |
| ds:ntype             |                    | — (shell)   | | |
| ds:parallel          |                    | —           | | Added to the original 2026-09-17 |
| ds:path_elements     | `ds path_elements` | ✅          | `test_simple_commands.py` | Tab-separated dir / stem / suffix |
| ds:pipe_check        |                    | —           | | |
| ds:pivot             | `ds pivot`         | ✅          | `test_pivot.py` | `--gen-keys` forces header-pattern keys |
| ds:plot              |                    | —           | | |
| ds:pow               | `ds power`         | ✅          | `test_power.py` | |
| ds:prod              | `ds prod`          | ✅*         | `test_prod.py` | |
| ds:random            | `ds random`        | ✅          | none | |
| ds:recent            |                    | —           | | |
| ds:reo               | `ds reo`           | ✅          | `test_reorder.py` | Indices/ranges, rev/others, expressions, searches, frames, anchors |
| ds:retry             |                    | —           | | Added to the original 2026-09-17 |
| ds:rev               | `ds rev`           | ✅          | `test_simple_commands.py` | Reads from stdin |
| ds:searchn           |                    | — (shell)   | | |
| ds:searchx           |                    | script only | | `curlies.py` exists but is not wired; hardcoded filename in `main()` |
| ds:sedi              |                    | —           | | |
| ds:select            |                    | —           | | |
| ds:shape             | `ds shape`         | ✅*         | `test_shape.py` | |
| ds:so                |                    | —           | | |
| ds:sort              |                    | —           | | |
| ds:sortm             | `ds sortm` / `ds s` | ✅*        | `test_sortm.py` | |
| ds:space             |                    | —           | | |
| ds:src               |                    | — (shell)   | | |
| ds:srg               |                    | —           | | |
| ds:stagger           | `ds stagger`       | ✅          | `test_stagger.py` | |
| ds:subsep            | `ds subsep`        | ✅          | `test_subseps.py` | Parity gap |
| ds:substr            |                    | —           | | |
| ds:test              | `ds test`          | ✅          | `test_test_command.py` | Quiet extended-regex check (stdin/string/file) |
| ds:tmp               |                    | —           | | |
| ds:todo              | `ds todo`          | ✅          | `test_simple_commands.py` | Prefers `rg` when cached on PATH; else Python scan |
| ds:trace             |                    | — (shell)   | | |
| ds:transpose         | `ds transpose` / `ds t` | ✅     | `test_simple_commands.py` | |
| ds:unicode           | `ds unicode`       | ✅          | `test_simple_commands.py` | |
| ds:uniq              | `ds field_uniques` / `ds u` | ✅ | `test_fieldcounts_uniq.py` | |
| ds:vi                | `ds vi`            | ✅          | `test_grep_edit.py` | Search files by name and open in `$EDITOR` |
| ds:websel            |                    | —           | | |

### Commands in dev_scripts_py with no original equivalent

| dev_scripts_py       | Status      | Tests | Notes |
| -------------------- | ----------- | ----- | ----- |
| `ds cardinality`     | ✅*         | `test_simple_commands.py` | Distinct values per field; port of the original `cardinality.awk` script, which has no `ds:*` wrapper there |
| `ds conda_check`     | ✅          | none | Check conda envs for packages |
| `ds conda_envs`      | ✅          | none | List conda environments with details |
| `ds version`         | ✅          | `test_build_info.py` | Version, plus build details for a standalone build |
| `tool_availability`  | internal    | | PATH probe cache (`rg`, etc.); `DS_REFRESH_TOOL_CACHE=1` clears |

### Unwired scripts (Python file exists, no CLI command)

| Script                    | Nearest original | Notes                                    |
| ------------------------- | ---------------- | ---------------------------------------- |
| `curlies.py`              | ds:searchx       | Hardcoded filename in `main()`           |
| `find_string_subparts.py` | —                | Utility functions only                   |
| `LocalMachineConfig.py`   | —                | Config class, has import error           |

## Completed ports

The 14 commands that carried a WIP or STUB marker were completed on 2026-11-21; no command in
`scripts/cli.py` carries `@wip` or `@stub` now (the decorators stay for future use). Each
entry lists the reference cases taken from the original's tests, the deliberate differences
from the original, and what is not ported. "Reference cases" were checked by running the
implementation module here against the original's expected output; the pytest files that
encode them have not been run yet (see the ✅* key above).

Shared by the data commands: an optional leading FILE or stdin via `CliArgContext`, the
field separator inferred unless `--field-sep` is given, and a whitespace separator splitting
on runs of whitespace (`scripts/field_rows.py`). If the separator cannot be inferred, these
commands stop with an error asking for `--field-sep` (see Known issues).

### Wiring and marker cleanup

- **`cardinality`**: unchanged logic, STUB marker removed; output test added.
- **`graph`**: WIP marker removed. Parent chains are followed iteratively and an indirect
  cycle (A→B→A) is reported as `CYCLENODE__ <node where the chain loops>` with exit code 1,
  where the previous code recursed until `RecursionError`. Reference cases: all 3 of
  `t_graph.sh` (already in `test_graph.py`).
- **`fit`**: wires the existing `FitColumns` port: `[FILE]`, `--field-sep`, `--buffer`,
  `--buffer-char`. `.csv` files are parsed as CSV so quoted fields may contain commas.
  Reference cases: `t_fit.sh` 'pipe case', 'base case', 'spaced quoted field case'.
  Difference: decimal columns follow `FitColumns`' own rules, so the 'bufferchar/decimal'
  fixture differs in width and zero formatting (`no_zero_blank`). Not ported: terminal-width
  truncation, gridlines, `d=` decimal options, partial fit by row/column pattern, multiple
  files.
- **`prod`**: one line set per FILE, piped stdin as the first set; lines kept as they are.
  Difference: the same file given twice is its product with itself (the original merges
  consecutive identical file names into one set). No original test.

### Small ports

- **`asgn`**: prints `lineno:line` for lines matching `[\w<>\[\]\-]+ *= *\S+`; FILE or
  stdin. Difference: always a Python scan, so the output format does not depend on whether
  `rg` is installed. No original test.
- **`enti`**: `[FILE]`, `--sep` (a space splits on whitespace, one other character
  literally, longer is a regex), `--min` (count ≥ min, default 1), `--order a|d`; ties sort by
  the whole output line as `sort -n` does. No original test.
- **`diff`**: own side-by-side diff (`difflib`) instead of GNU `diff -y`, so it runs on Windows.
  `FILE1|STR1 FILE2|STR2` or the first input on stdin; `--suppress-common`, `--width`;
  whitespace-amount changes ignored as with `diff -b`; changed characters coloured on a
  terminal (`--no-color` turns this off). The previous `DiffColor` class failed on every
  changed line (`coloron` read before assignment) and is replaced. Not ported: pager output.
  No original test.

### Medium ports

- **`inferh`**: scoring formula ported in full. Exit 0 = header, 1 = no header or fewer than
  two rows; `--field-sep`, `--max-rows`, `--verbose` (prints the score). Reference cases: all
  19 active `inferh` cases of `t_infer.sh`, with the separator the original infers for each.
  The `/i` regex suffix in the original's column-name checks is treated as case-insensitive
  matching, as in `dsr`.
- **`sortm`**: `[FILE] [KEYS] [ORDER] [TYPE]`, `--header`, `--deterministic` (the default when
  KEYS is omitted, as in the original wrapper). Comparison follows the original: a single
  numeric-looking key compares numerically, joined keys as strings, type `n` by leading
  number then the rest, with keys without a number compared as strings against the number.
  Reference cases: `t_sort.sh` 'multikey', 'awkargs', 'numeric sort', 'numeric sort gen
  keys', 'case-insensitive keyfield 2'. Difference: equal keys keep input order (the
  original's quicksort is not stable). Not ported: `multisort` (3 cases), custom `-F` regex
  separators.
- **`hist`**: `[FILE] [N_BINS] [BAR_LEN]`, `--header`, `--fields`; header detection, integer
  bins and edge precision as in the original, including its six-significant-digit keys for
  distinct values and bin edges. Reference cases: `t_shape.sh` 'hist command' (crime data),
  plus the bins and counts of the 'blocks style' and edge cases. Difference: without a header
  row the first row is counted as data (the original drops it). Not ported: bar styles,
  colour, log bins, cumulative, stats/percentiles.
- **`shape`**: `[FILE] [MEASURES] [FIELDS] [CHART_SIZE]`, `--header`, `--tty-size`; several
  measures side by side as in the original. Reference cases: `t_shape.sh` 'shape command'
  (3 cases, including four measures at width 238), 'case-insensitive', and the plus-style
  default case. Difference: trailing padding is trimmed. Not ported: stats, normalize,
  vertical, colour, styles other than `+`, `case_sensitive`.

### Large ports

- **`diff_fields`**: `FILE1 FILE2 [OP] [EXCLUDE_FIELDS]` or `FILE1` with the second on stdin;
  ops `- + * / %`, `b`, `m` (MAD), `r` (RMSD), `s` (stats); `--header`, `--precision`,
  `--diff-list on|only`, `--diff-list-sort d|a|off`. A value counts as a number when it is
  numeric after removing thousands commas. Reference cases: `t_diff_fields.sh` base,
  percent diff list, divide diff list only, percent diff list header, multiply header,
  precision; MAD/RMSD/stats for fields 2-4. Differences: the summary ops report every
  counted field (the original's loop runs to the number of counted fields, which drops the
  last one in its own test), `Min` is the true minimum (the original resets a minimum of 0),
  and `b` prints one value per field. Not ported: multiple files, thresholds, highlighting,
  `extract_vals`.
- **`inferk`**: the simplified heuristic chosen for `dsr`: a header name shared by both files
  wins, otherwise the column pair with the highest Jaccard similarity of up to 50 sampled
  values, minus a tenth of the cardinality-ratio difference; `--fs1`, `--fs2`, `--no-header`,
  `--max-rows`. Reference cases: 8 of 10 in `t_inferk.sh`. Not matching: 'numeric
  distribution' and 'cardinality', where two columns overlap equally and the first pair wins
  while the original's score prefers the later one.
- **`agg`**: `[FILE] [R_AGGS] [C_AGGS]`, `--header`. Expressions `OP`, `OP|all`,
  `OP|START..END` with `+`, `-` (negated sum), `*`, `/` (first divided by the rest), `m`/`mean`;
  a scope means fields for row aggregates and line numbers (header line included) for column
  aggregates, as the original's tests show. Default `+|all` on both axes only when neither is
  given; `0` turns an axis off. Reference cases: 11 of `t_aggregation.sh` (all range and
  default cases, one with its `$2/$3` row left out). Not ported: field-index expressions
  (`$1+$3`), header-name references, `~pattern`, comparisons, cross-aggregation,
  `med`/`mode`/`sd`/quartiles, `extract_vals`, terminal fitting of the output.

## Parity gaps

Original commits after the corresponding Python port (dates from the original's commit log):

| Command | Original change | Python last changed |
| ------- | --------------- | ------------------- |
| `case` | 2026-09-09 "Enable dash case"; 2026-09-17 "Fixes and improvements to case command logic for dashes" | 2026-08-24 |
| `subsep` | 2026-09-17 "Improvement to subseps command" (`subseparator.awk` +61, `t_subsep.sh` +26) | 2026-08-24 |
| `git_purge_local` | 2026-09-21 "Fixes and improvements to git purge local branches script, add tests" (`purge_local_branches.sh` +85, new `t_git_purge.sh`) | 2026-09-17 |

These are outside the completion scope above, but they need porting for the Python
commands to match the current original.

## Not ported

Portable, not yet ported: `color`, `deps2`, `dup_input`, `gexec`, `mini`, `parallel`,
`pipe_check`, `plot`, `recent`, `retry`, `searchx` (script only), `sedi`, `select`, `so`,
`sort`, `space`, `srg`, `substr`, `tmp`, `websel`.

Shell-session commands (— (shell) above): `deps`, `fail`, `fsrc`, `new`, `nset`, `ntype`,
`searchn`, `src`, `trace`. `dsr` ports these with reduced, explicitly documented behaviour
(`cd` prints a path instead of changing directory, `nset`/`ntype`/`searchn` check only
exported environment variables and PATH programs, `src`/`fsrc`/`deps` work on a given file,
`trace` runs the command in its own `sh -x` subshell). The same approach would work here
if these are wanted. `ds cd` already follows it.

## Conventions for completing the port

Adopted from the Rust port (`dev_scripts_rust`) so the ports stay consistent. `dev_scripts_c`
only documents the module-per-command and test-per-command structure, which this project
already uses.

- **Core functionality first, gaps documented.** Each command ports its documented core use
  case. Original options that are left out are listed in this file under the command,
  together with any deliberate behaviour difference. A user can then tell an intentional
  simplification from a bug.
- **Architectural limits are separate from simplifications.** A command that cannot behave
  like the original because it runs as a separate process (the — (shell) group) is marked as
  such, not as merely incomplete.
- **Test parity against the original's tests, only for hand-verifiable cases.** New pytest
  cases mirror assertions from the original `tests/t_*.sh` file named under "Original"
  above, one test per assertion. A case is only added if its expected output can be derived
  by reading both the original and the Python code. Cases that cannot be derived reliably
  without running the original (complex heuristics, long decimal output) are noted as not
  ported, not filled with a guessed expectation. Fixtures go in `tests/data/`.
- **Verification state is recorded.** `click` and `pytest` are not importable in the agent
  sandbox, so changes made there are checked with `python3 -m py_compile` and by running the
  click-free implementation modules directly. A command counts as done once
  `python run_tests.py` has passed outside the sandbox. Until then, its entry is marked ✅*.
- **Stdin vs. file arguments go through `CliArgContext`.** New data commands use
  `CliArgContext.from_click` with `PathCandidatePredicate.TESTED_FIRST_ARG` like `index`,
  `reo` and `subsep`, so an optional leading FILE can be followed by further positional
  arguments with data on stdin. `dsr` needed an explicit `-` placeholder for the same
  problem. Two-input commands (`diff_fields`, `inferk`) use
  `PathCandidatePredicate.PAIR_CHAIN_OR_STDIN_SECOND` like `matches`.
- **Terminal vs. pipe output.** In the original, `agg`, `diff_fields`, `pivot`, `join`,
  `matches`, `comps`, `power`, `field_counts`, `field_uniques`, `transpose`, `reo` and
  `field_replace` pass output through `ds:ttyf`: column-fitted when stdout is a terminal,
  raw otherwise. `dsr` reproduces this with a shared helper. This project does not do this
  yet. With `ds fit` wired, the same can be added via `FitColumns` once it is decided
  whether that is wanted. Not part of the completion scope.

## Known issues outside the completion scope

Found while completing the port. Not fixed yet:

- Separator inference (`ds inferfs`, and every command that infers a separator) fails with
  `AttributeError: 'NoneType' object has no attribute 'span'` in `get_nf`
  (`scripts/infer_field_separator.py`, at the existing `# TODO fix`) for input with double
  quotes, e.g. `tests/data/addresses_reordered`, `tests/data/ls_sq`, or a CSV with quoted
  fields. It also infers `:` for comma-separated data with timestamps and a space for
  comma-separated HTML snippets, where the original infers a comma (`t_infer.sh`
  'time-related headers', 'HTML/XML fields').
- When the separator cannot be inferred, `reo`, `subsep` and `pivot` fall back to whitespace
  silently, while the commands completed here stop with an error asking for `--field-sep`.
- `ds join`: docstring (and so its help text) is a copy of `index`'s ("Print lines indexed").
- The repository root of the workspace holds an older copy of this file (2026-02-16), which
  this file supersedes.

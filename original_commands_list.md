A mapping of the original commands list (below) to the ported commands in this project.

```log
    COMMAND              ALIAS    DESCRIPTION                                      USAGE

**  ds:agg                        Aggregate by index/pattern                       ds:agg [-h|file*] [r_aggs=+] [c_aggs=+]
    ds:asgn                       Print lines matching assignment pattern          ds:asgn file
**  ds:case                       Recase text data globally or in part             ds:case [string] [tocase=proper] [filter]
    ds:cd                         cd to higher or lower level dirs                 ds:cd [search]
**  ds:color                      Get RGB from hex or hex from RGB                 ds:color [hex|rgb|r] [g] [b]
    ds:commands                   List dev_scripts commands                        ds:commands [bufferchar] [utils] [re_source]
**  ds:comps                      Get non-matching lines from two datasets         ds:comps file [file] [awkargs]
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
**  ds:line                       Execute commands on var line                     ds:line [seed_cmds] line_cmds [IFS=\n]
**  ds:matches                    Get match lines from two datasets                ds:matches file [file] [awkargs]
**  ds:mini                       Crude minify, remove whitespace and newlines     ds:mini [file*] [newline_sep=;] [blank_only=f]
    ds:new                        Refresh zsh or bash interactive session          ds:new
**  ds:newfs                      Convert field separators - i.e. tsv -> csv       ds:newfs [file] [newfs=,] [awkargs]
    ds:nset                       Test name (function/alias/variable) is defined   ds:nset name [search_vars=f]
    ds:ntype                      Get name type - function, alias, variable        ds:ntype name
    ds:path_elements              Return dirname/filename/extension from filepath  read -r dirpath filename extension <<< "$(ds:path_elements file)"
**  ds:pipe_check                 Detect if pipe has data or over [n_lines]        data | ds:pipe_check [n_lines]
**  ds:pivot                      Pivot tabular data                               ds:pivot [file] [y_keys] [x_keys] [z_keys=count_xy] [agg_type]
    ds:plot                       Get a scatter plot of from two fields            ds:plot [file] [field_y=1] [field_x=index]
**  ds:pow                        Combinatorial frequency of data field values     ds:pow [file] [min] [return_fields=f] [invert=f] [awkargs]
**  ds:prod                       Return product multiset of filelines             ds:prod file [file*] [awkargs]
**  ds:random                     Generate a random number 0-1 or randomize text   ds:random [number|text]
    ds:recent                     List files modified recently                     ds:recent [dir=.] [days=7] [recurse=f] [hidden=f] [only_files=f]
**  ds:reo                        Reorder/repeat/slice data by rows and cols       ds:reo [-h|file*] [rows] [cols] [prefield=t] [awkargs]
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

Mapping:

Status key: ✅ = fully wired, WIP = wired with warning, STUB = wired but hidden by default, script only = Python file exists but not wired to CLI, — = not ported.

| Original             | dev_scripts_py     | Status      | Notes                                        |
| -------------------- | ------------------ | ----------- | -------------------------------------------- |
| ds:agg               | `ds agg`           | WIP         |                                              |
| ds:asgn              | `ds asgn`          | WIP         |                                              |
| ds:case              | `ds case`          | ✅          |                                              |
| ds:cd                | `ds cd`            | ✅          | Resolves a target path for shell `cd` usage  |
| ds:color             |                    | —           |                                              |
| ds:commands          | `ds commands`      | ✅          | Also available via `ds --help`               |
| ds:comps             | `ds comps`         | ✅          | Complement of `ds matches`                   |
| ds:cp                | `ds cp`            | ✅          | Clipboard (UTF-8); macOS ``pbcopy``, Win PS, Linux xclip/wl-copy/xsel |
| ds:decap             | `ds decap`         | ✅          | Drop first *n* lines (file or stdin)         |
| ds:deps              |                    | —           | Shell-specific                               |
| ds:deps2             |                    | —           |                                              |
| ds:diff              | `ds diff`          | STUB        | Runs side-by-side diff, colorized via `diff_color.py` |
| ds:diff_fields       | `ds diff_fields`   | STUB        | References undefined globals in process_lines |
| ds:dostounix         | `ds dostounix`     | ✅          | In-place for files; stdin->stdout normalized |
| ds:dup_input         |                    | —           |                                              |
| ds:dups              | `ds dup_files`     | ✅          |                                              |
| ds:embrace           | `ds embrace`       | ✅          |                                              |
| ds:enti              | `ds enti`          | STUB        |                                              |
| ds:fail              |                    | —           | Shell-specific                               |
| ds:field_replace     | `ds field_replace` | ✅          | Supports [FILE] or stdin, expression/key/pattern |
| ds:fieldcounts       | `ds field_counts`  | ✅          |                                              |
| ds:filename_str      |                    | —           |                                              |
| ds:fit               | `ds fit`           | STUB        | All methods are stubs                        |
| ds:fsrc              |                    | —           | Shell-specific                               |
| ds:gexec             |                    | —           |                                              |
| ds:git_add_com_push  | `ds git_add_com_push` / `ds gacp` | ✅ |                                              |
| ds:git_branch        | `ds git_branch` / `ds gb` | ✅    |                                              |
| ds:git_branch_refs   | `ds git_branch_refs` / `ds gbr` | ✅ |                                              |
| ds:git_checkout      | `ds git_checkout` / `ds gco` | ✅   |                                              |
| ds:git_cross_view    | `ds git_cross_view` / `ds gcv` | ✅ |                                              |
| ds:git_diff          | `ds git_diff`      | ✅          |                                              |
| ds:git_graph         | `ds git_graph` / `ds gg` | ✅     |                                              |
| ds:git_purge_local   | `ds git_purge_local` / `ds gpl` | ✅ |                                              |
| ds:git_recent        | `ds git_recent` / `ds gr` | ✅     |                                              |
| ds:git_recent_all    | `ds git_recent_all` / `ds gra` | ✅ |                                              |
| ds:git_refresh       | `ds git_refresh` / `ds grf` | ✅   |                                              |
| ds:git_squash        | `ds git_squash` / `ds gsq` | ✅    |                                              |
| ds:git_status        | `ds git_status` / `ds gs` | ✅     |                                              |
| ds:git_time_stat     | `ds git_time_stat` / `ds gts` | ✅  |                                              |
| ds:git_word_diff     | `ds git_word_diff` / `ds gwdf` | ✅ |                                              |
| ds:goog              | `ds goog`          | ✅          | Opens browser search URL                      |
| ds:graph             | `ds graph`         | WIP         | Reads from stdin                             |
| ds:grepvi            | `ds grepvi`        | ✅          | Grep content and open in `$EDITOR`           |
| ds:help              | `ds --help`        | ✅          | Also `ds commands`                           |
| ds:hist              | `ds hist`          | WIP         | Incomplete (truncated after binning)         |
| ds:index             | `ds index`         | ✅          |                                              |
| ds:inferfs           | `ds inferfs`       | ✅          |                                              |
| ds:inferh            | `ds inferh`        | STUB        | Still AWK, not yet ported to Python          |
| ds:inferk            | `ds inferk`        | STUB        | Script has mixed AWK/Python syntax           |
| ds:insert            | `ds insert`        | ✅          | Supports stdin/file/string insertion source   |
| ds:iter              | `ds iter`          | ✅          |                                              |
| ds:jira              | `ds jira`          | ✅          | Opens Jira workspace/issue/search URL         |
| ds:join              | `ds join`          | ✅          |                                              |
| ds:join_by           | `ds join_by`       | ✅          |                                              |
| ds:line              | `ds line`          | ✅          | Supports `{line}` placeholder in command      |
| ds:matches           | `ds matches`       | ✅          | Two paths or one path + stdin; `-k` / `--key1` / `--key2`, `--verbose` |
| ds:mini              |                    | —           |                                              |
| ds:new               |                    | —           | Shell-specific                               |
| ds:newfs             | `ds newfs`         | ✅          | Convert field separators (file or stdin)     |
| ds:nset              |                    | —           | Shell-specific; see `tool_availability` (Python) |
| ds:ntype             |                    | —           | Shell-specific                               |
| ds:path_elements     | `ds path_elements` | ✅          | Tab-separated dir / stem / suffix            |
| ds:pipe_check        |                    | —           |                                              |
| ds:pivot             | `ds pivot`         | WIP         | Undefined `prod()` in aggregate              |
| ds:plot              |                    | —           |                                              |
| ds:pow               | `ds power`         | ✅          |                                              |
| ds:prod              | `ds prod`          | STUB        |                                              |
| ds:random            | `ds random`        | ✅          |                                              |
| ds:recent            |                    | —           |                                              |
| ds:reo               | `ds reo`           | STUB        | All methods are stubs                        |
| ds:rev               | `ds rev`           | ✅          | Reads from stdin                              |
| ds:searchn           |                    | —           | Shell-specific                               |
| ds:searchx           |                    | script only | `curlies.py` exists but not wired            |
| ds:sedi              |                    | —           |                                              |
| ds:select            |                    | —           |                                              |
| ds:shape             | `ds shape`         | STUB        |                                              |
| ds:so                |                    | —           |                                              |
| ds:sort              |                    | —           |                                              |
| ds:sortm             | `ds sortm`         | STUB        | Many incomplete methods                      |
| ds:space             |                    | —           |                                              |
| ds:src               |                    | —           | Shell-specific                               |
| ds:srg               |                    | —           |                                              |
| ds:stagger           | `ds stagger`       | ✅          | Dedicated parity-focused tests in `test_stagger.py` |
| ds:subsep            | `ds subsep`        | STUB        | Core methods incomplete (`SetOFS` etc.); many parity tests skipped |
| ds:substr            |                    | —           |                                              |
| ds:test              | `ds test`          | ✅          | Quiet extended-regex check (stdin/string/file) |
| ds:tmp               |                    | —           |                                              |
| ds:todo              | `ds todo`          | ✅          | Prefers `rg` when cached on PATH; else Python scan |
| ds:trace             |                    | —           | Shell-specific                               |
| ds:transpose         | `ds transpose`     | ✅          |                                              |
| ds:unicode           | `ds unicode`       | ✅          |                                              |
| ds:uniq              | `ds field_uniques` | ✅          | Parity tests in `test_fieldcounts_uniq.py`   |
| ds:vi                | `ds vi`            | ✅          | Search files by name and open in `$EDITOR`   |
| ds:websel            |                    | —           |                                              |

### Commands in dev_scripts_py with no original equivalent

| dev_scripts_py       | Status      | Notes                                        |
| -------------------- | ----------- | -------------------------------------------- |
| `ds kill_port`       | ✅          | Kill processes bound to a port               |
| `ds move`            | ✅          | Move files/dirs with filtering               |
| `ds copy`            | ✅          | Copy files/dirs with filtering               |
| `ds conda_check`     | ✅          | Check conda envs for packages                |
| `ds conda_envs`      | ✅          | List conda environments with details         |
| `ds cardinality`     | STUB        | Distinct values per field                    |
| `tool_availability`  | internal    | PATH probe cache (`rg`, etc.); `DS_REFRESH_TOOL_CACHE=1` clears |

### Unwired scripts (Python file exists, no CLI command)

| Script                    | Nearest original | Notes                                    |
| ------------------------- | ---------------- | ---------------------------------------- |
| `curlies.py`              | ds:searchx       | Hardcoded filename in main()             |
| `find_string_subparts.py` | —                | Utility functions only                   |
| `LocalMachineConfig.py`   | —                | Config class, has import error           |

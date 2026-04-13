---
name: LaTeX report file structure
description: File layout of the MTech report and which files contain which chapters
type: project
---

Report root: `/home/avadh/Avadh/shell/MTech_Report_Avadh/`

Main entry point: `Sample_Report.tex` — contains the preamble and \include{} directives.

Implementation chapter: `Implementation.tex` — standalone file included by Sample_Report.tex.

The `xcolor` package (`\usepackage{xcolor}`) was added to `Sample_Report.tex` during the Sprint 0 update and is confirmed present.

**Why:** Need to know exact file paths so edits target the right file without a directory scan.

**How to apply:** All Implementation chapter edits go to `Implementation.tex`. Preamble changes (if ever needed) go to `Sample_Report.tex`.

## Current sections in Implementation.tex (as of Sprint 1 deep-dive + abstract-findings update, 2026-04-13)

1. `\chapter{Implementation}` — opening paragraph describing CV + LLM system overview.
2. `\section{\textcolor{red}{Foundation Infrastructure (Sprint 0)}}` — frozen event vocabulary, logbase schema, simulator scaffold, directory layout (all red).
3. `\section{\textcolor{red}{B1 NL→SQL Approach --- Sprint 1 Implementation}}` — intro paragraph (all red). Subsections:
   - `\subsection{\textcolor{red}{Two-Step B1 Architecture}}` — SQL Generator, SQL Validator, SQL Executor, One-Shot SQL Repair, Step 2 Answer Synthesiser, Transient-Error Retry (all red).
   - `\subsection{\textcolor{red}{Schema-Description Prompt Design}}` — DDL, semantic rules, time-filter idioms, index list, SQLite-dialect constraints, schema-priming framing; cites Yu2018Spider, Li2023BIRD, Pourreza2023DINSQL (all red, ADDED 2026-04-13).
   - `\subsection{\textcolor{red}{SQL Validator}}` — regex rules, defense-in-depth framing (all red, ADDED 2026-04-13).
   - `\subsection{\textcolor{red}{One-Shot SQL Repair Loop}}` — OperationalError trigger, repair prompt, concrete L3_q002 example, DIN-SQL reference (all red, ADDED 2026-04-13).
   - `\subsection{\textcolor{red}{Transient-Error Retry}}` — 3-attempt backoff, Sprint 1 v2/v3 justification (all red, ADDED 2026-04-13).
   - `\subsection{\textcolor{red}{Session-Context Injection}}` — abstract operator phrasing problem, scenario JSON lookup, SESSION CONTEXT preamble, production-UI framing (all red, ADDED 2026-04-13).
   - `\subsection{\textcolor{red}{Answer Envelope}}` — 6-field uniform dict, B1/B2 head-to-head contract (all red, ADDED 2026-04-13).
   - `\subsection{\textcolor{red}{Themed Evaluation Scenario --- AI Hardware Summit 2025}}` — 8 cameras, crowd/entry layout, 437,940 events (all red).
   - `\subsection{\textcolor{red}{L1--L5 Benchmark Authoring}}` — 11-question distribution, scorer fixes (all red).
   - `\subsection{\textcolor{red}{Sprint 1 Benchmark Results}}` — pass-rate table (label: tab:sprint1_results), 14/14 L1–L3 summary (all red).
4. `\section{\textcolor{red}{Sprint 1 Findings: LLM Behaviour on Abstract Real-User Questions}}` — 41-question bench (26 schema-aware + 15 abstract), 86.6% overall, 5 LLM-behaviour findings itemised, closing contribution paragraph; cites Yu2018Spider, Li2023BIRD (all red, ADDED 2026-04-13).
5. `\section{System Architecture Overview}` — four-module pipeline, system flow figure.
6. `\section{CCTV Nodes and Computer Vision Event Detection}` — YOLOv8, event ID, tracking (DeepSORT/ByteTrack now has citations), MQTT message passing.
7. `\section{Central Database & Event Log Storage}` — logbase schema, sample JSON, field descriptions.
8. `\section{LLM Integration for Surveillance Analytics}` — real-time query interpretation, insight generation.
9. `\section{Insight Delivery to End Users}` — output formats.
10. `\section{Implementation Summary}` — bullet summary + Demo subsection with screenshot figure.

## Citations added so far (all in red additions)
- `\cite{Pourreza2023DINSQL}` — DIN-SQL self-correction; Schema-Description Prompt Design + One-Shot Repair Loop subsections
- `\cite{Yu2018Spider}` — Spider benchmark; Schema-Description Prompt Design, L1–L5 Bench Authoring, Abstract Findings closing paragraph
- `\cite{Li2023BIRD}` — BIRD benchmark; Schema-Description Prompt Design, L1–L5 Bench Authoring, Abstract Findings closing paragraph
- `\cite{Wojke2017DeepSORT}` — DeepSORT tracker citation (CCTV section, tracking bullet)
- `\cite{Zhang2022ByteTrack}` — ByteTrack citation (CCTV section, tracking bullet)

These keys must exist in `mybib.bib`.

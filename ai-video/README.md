# AI Video Creation Website

This directory contains a self-contained product brief and frontend scaffold for an Idea → Script → Video application.

The GitHub connector used in this session cannot create a brand-new repository, so this scaffold is stored in the accessible repository as `ai-video/`. Move these files into a new repository named `AI-Video-Creation-Website` when creating it from GitHub.

## Product

Users type one idea. The application generates a structured script, scene plan, narration, visuals, captions, music and an edit timeline, then renders the final video through provider adapters.

## Architecture

- Web UI: Next.js / React / TypeScript
- Script AI: LLM provider adapter
- Visuals: stock-media search + image/video generation adapters
- Voice: TTS adapter
- Captions: transcript/word timing adapter
- Rendering: server-side FFmpeg/Remotion-style adapter
- Storage: object storage for assets and renders

## Production provider wiring

The current scaffold uses a deterministic mock pipeline so the UI works without API keys. Replace the adapter functions with production providers and keep credentials server-side.

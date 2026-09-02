# API design

## POST /api/generate-script
Input:
```json
{"idea":"Best features in ChatGPT","language":"English","tone":"Energetic","duration":"60 sec","format":"Short-form"}
```

Output:
```json
{
  "title":"Best features in ChatGPT",
  "scenes":[
    {
      "id":"scene-1",
      "duration":5,
      "narration":"...",
      "visual_query":"...",
      "overlay":"...",
      "transition":"..."
    }
  ],
  "cta":"..."
}
```

## POST /api/render
Takes the generated scene plan and returns a render job ID. A worker should resolve media, synthesize voice, generate captions/timing and render the final MP4.

## Provider adapter contracts

```ts
interface ScriptProvider {
  generate(input: ScriptInput): Promise<VideoPlan>
}
interface VoiceProvider {
  synthesize(text: string, options: VoiceOptions): Promise<AudioAsset>
}
interface MediaProvider {
  search(query: string, options: MediaOptions): Promise<MediaAsset[]>
}
interface RenderProvider {
  render(timeline: Timeline): Promise<RenderJob>
}
```

Keep all provider API keys on the server. Persist generated assets and job status in a database/object store for production deployments.

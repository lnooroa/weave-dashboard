// Cloudflare Pages Function: POST /chat
export async function onRequestOptions() {
  return new Response(null, {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Headers": "content-type",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    },
  });
}

export async function onRequestPost({ request, env }) {
  try {
    const body = await request.json();
    const messages = body?.messages ?? [];

    const r = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GROQ_API_KEY}`,
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: env.GROQ_MODEL || "llama-3.1-8b-instant",
        temperature: 0.2,
        messages,
      }),
    });

    const data = await r.json();
    const content = data?.choices?.[0]?.message?.content ?? JSON.stringify(data);
    return new Response(
      JSON.stringify({ choices: [{ message: { content } }] }),
      { headers: { "content-type": "application/json", "Access-Control-Allow-Origin": "*" } }
    );
  } catch (e) {
    return new Response(
      JSON.stringify({ choices: [{ message: { content: `(router error) ${e}` } }] }),
      { headers: { "content-type": "application/json", "Access-Control-Allow-Origin": "*" }, status: 200 }
    );
  }
}

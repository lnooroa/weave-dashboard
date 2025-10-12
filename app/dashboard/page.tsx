'use client';
import { useState } from 'react';

async function postJSON(url: string, data: any) {
  const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  try { return await res.json(); } catch { return { ok:false, status: res.status }; }
}

export default function Dashboard() {
  const [slug, setSlug] = useState('');
  const [title, setTitle] = useState('GEN: page /hello3');
  const [status, setStatus] = useState<string>('');
  const repo = "lnooroa/weave-dashboard";

  async function createIssue() {
    setStatus('Submitting…');
    const r = await postJSON('/api/issue', { title, body: '' });
    setStatus(r?.ok ? `Opened issue #${r.number}` : `Issue failed: ${r?.status || r?.error || 'error'}`);
  }

  function issueLink(t: string) {
    const pre = `https://github.com/${repo}/issues/new?title=`;
    return pre + encodeURIComponent(t);
  }

  return (
    <main style={{ padding: 24, fontFamily: "system-ui, Arial" }}>
      <h1>Weave Dashboard</h1>

      <section style={{ marginTop: 16 }}>
        <h3>Generate Page (no typing)</h3>
        <p>Tap a link to open a prefilled GitHub Issue (fallback mode):</p>
        <ul>
          <li><a target="_blank" href={issueLink("GEN: page /hello2")}>Create /hello2</a></li>
          <li><a target="_blank" href={issueLink("GEN: page /about")}>Create /about</a></li>
          <li><a target="_blank" href={issueLink("DEL: page /about")}>Delete /about</a></li>
          <li><a target="_blank" href={issueLink("UPGRADE: dashboard v1")}>Re-run upgrade</a></li>
        </ul>
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>Native buttons (no GitHub screen)</h3>
        <p style={{ fontSize: 14, opacity: 0.8 }}>
          Works when a <code>GH_TOKEN</code> is set in Vercel. Otherwise the buttons will tell you to add it.
        </p>

        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
          <input
            placeholder="slug (e.g. blog)"
            value={slug}
            onChange={e => setSlug(e.target.value)}
            style={{ padding: 8, border: "1px solid #ccc", borderRadius: 8 }}
          />
          <button
            onClick={async () => {
              const s = (slug || '').replace(/[^a-z0-9/_-]/gi,'').replace(/^\/+/,'');
              if (!s) { setStatus('Enter a slug'); return; }
              setStatus('Submitting…');
              const r = await postJSON('/api/issue', { title:`GEN: page /${s}`, body:'' });
              setStatus(r?.ok ? `Opened issue #${r.number}` : `Issue failed: ${r?.status || r?.error || 'error'}`);
            }}
            style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #888" }}
          >
            Generate /{slug || '…'}
          </button>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 12 }}>
          <input
            placeholder='Issue title (e.g. "GEN: page /contact")'
            value={title}
            onChange={e => setTitle(e.target.value)}
            style={{ flex: 1, padding: 8, border: "1px solid #ccc", borderRadius: 8 }}
          />
          <button onClick={createIssue} style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #888" }}>
            Send
          </button>
        </div>

        <p style={{ marginTop: 8, fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace", fontSize: 13 }}>{status}</p>
      </section>

      <section style={{ marginTop: 24 }}>
        <h3>Health</h3>
        <ul style={{ fontSize: 14 }}>
          <li>API: <a href="/api/health" target="_blank">/api/health</a></li>
          <li>Repo: {repo}</li>
        </ul>
      </section>
    </main>
  );
}

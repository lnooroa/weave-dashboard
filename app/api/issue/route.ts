import { NextResponse } from "next/server";
const REPO = "lnooroa/weave-dashboard";
export async function POST(req: Request) {
  try {
    const token = process.env.GH_TOKEN;
    const { title, body } = await req.json();
    if (!token) return NextResponse.json({ ok:false, error:"Missing GH_TOKEN" }, { status: 400 });
    if (!title) return NextResponse.json({ ok:false, error:"Missing title" }, { status: 400 });

    const r = await fetch(`https://api.github.com/repos/${REPO}/issues`, {
      method: "POST",
      headers: {
        "Authorization": `token ${token}`,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ title, body: body || "" })
    });
    const json = await r.json();
    if (!r.ok) return NextResponse.json({ ok:false, status:r.status, error: json?.message || "GitHub error" }, { status: 500 });
    return NextResponse.json({ ok:true, number: json.number, url: json.html_url });
  } catch (e:any) {
    return NextResponse.json({ ok:false, error: e?.message || "error" }, { status: 500 });
  }
}

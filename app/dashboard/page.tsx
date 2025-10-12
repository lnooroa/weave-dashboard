export default function Dashboard() {
  return (
    <main style={{ padding: 24, fontFamily: "system-ui, Arial" }}>
      <h1>Weave Dashboard</h1>
      <p>Tap a link to open a prefilled Issue:</p>
      <ul>
        <li><a target="_blank" href="https://github.com/lnooroa/weave-dashboard/issues/new?title=GEN:%20page%20/hello2">Create /hello2</a></li>
        <li><a target="_blank" href="https://github.com/lnooroa/weave-dashboard/issues/new?title=GEN:%20page%20/about">Create /about</a></li>
        <li><a target="_blank" href="https://github.com/lnooroa/weave-dashboard/issues/new?title=DEL:%20page%20/about">Delete /about</a></li>
      </ul>
    </main>
  );
}

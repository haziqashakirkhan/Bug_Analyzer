const $ = (id) => document.getElementById(id);
const form = $("form"), bug = $("bug"), go = $("go");
const stepsEl = $("steps"), emptyEl = $("empty"), errorEl = $("error"), reportEl = $("report");
const order = ["bug_analysis", "severity_detection", "root_cause", "format_report"];
let finalReport = "";

const EXAMPLES = [
  "When I click \"Pay Now\" on the checkout page with a saved card, the page freezes and I get charged twice. It happens on Chrome and Safari for every order since yesterday's release.",
  "Searching for a product by name takes 15 to 20 seconds to return results on the mobile app. It was instant last week. Only happens when the query has more than two words.",
  "The company logo in the top-left of the dashboard is shifted about 10px to the right on screens narrower than 1024px. Everything else works fine."
];

bug.addEventListener("input", () => { $("count").textContent = `${bug.value.length} / 5000`; });
document.querySelectorAll(".chip").forEach((b) =>
  b.addEventListener("click", () => {
    bug.value = EXAMPLES[b.dataset.ex];
    bug.dispatchEvent(new Event("input"));
    bug.focus();
  })
);
bug.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) form.requestSubmit();
});

function setSteps(activeIdx) {
  stepsEl.querySelectorAll("li").forEach((li, i) => {
    li.classList.toggle("done", i < activeIdx);
    li.classList.toggle("active", i === activeIdx);
  });
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.hidden = false;
  stepsEl.hidden = true;
  emptyEl.hidden = true;
}

function renderReport(r) {
  reportEl.dataset.severity = r.severity;
  $("r-sev").textContent = r.severity;
  $("r-title").textContent = r.title;
  $("r-feature").textContent = r.affected_feature;
  $("r-summary").textContent = r.summary;
  $("r-reason").textContent = r.severity_reason;
  const list = $("r-causes");
  list.replaceChildren(...r.root_causes.map((c) => Object.assign(document.createElement("li"), { textContent: c })));
  finalReport = r.final_report || "";
  reportEl.hidden = false;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = bug.value.trim();
  errorEl.hidden = true;
  reportEl.hidden = true;
  emptyEl.hidden = true;

  if (text.length < 15) return showError("Add a bit more detail (at least a sentence) so the analysis is useful.");

  go.disabled = true;
  go.textContent = "Analyzing…";
  stepsEl.hidden = false;
  setSteps(0);
  const result = {};

  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bug_description: text }),
    });
    if (!res.ok) throw new Error((await res.json()).error || "The server rejected the request.");

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines.filter(Boolean)) {
        const msg = JSON.parse(line);
        if (msg.error) throw new Error(msg.error);
        Object.assign(result, msg.data);
        setSteps(order.indexOf(msg.node) + 1);
      }
    }
    if (!result.final_report) throw new Error("The analysis ended before the report was ready. Try again.");
    renderReport(result);
  } catch (err) {
    showError(`Analysis failed: ${err.message}`);
  } finally {
    go.disabled = false;
    go.textContent = "Analyze bug";
  }
});

$("copy").addEventListener("click", async (e) => {
  try {
    await navigator.clipboard.writeText(finalReport);
    e.target.textContent = "Copied";
  } catch {
    e.target.textContent = "Copy failed";
  }
  setTimeout(() => (e.target.textContent = "Copy report"), 1600);
});

$("reset").addEventListener("click", () => {
  reportEl.hidden = true;
  stepsEl.hidden = true;
  errorEl.hidden = true;
  emptyEl.hidden = false;
  bug.value = "";
  bug.dispatchEvent(new Event("input"));
  bug.focus();
});
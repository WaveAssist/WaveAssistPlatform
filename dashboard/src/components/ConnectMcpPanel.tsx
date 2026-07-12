import React, { useEffect, useState } from "react";
import { Modal } from "react-bootstrap";
import { MCP_URL, MCP_MARKETPLACE } from "../config/branding";
import { fetchBillingOverview } from "../services/all_projects_services";
import { regenerateMcpToken } from "../services/account_services";
import { useToast } from "../utils/toast_context";

// The Connect MCP panel: shows the user's identity + rotatable MCP bearer token and
// copy-paste connection snippets for Claude Code (CLI + plugin) and Cursor / any MCP
// host, all pointed at the already-hosted WaveAgent server. UID stays the identity for
// every other API; the token is only the MCP bearer and can be rotated here.

const mono = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

const CodeBlock: React.FC<{ label: string; code: string; onCopy: (t: string) => void }> = ({ label, code, onCopy }) => (
	<div style={{ marginBottom: 16 }}>
		<div style={{ fontFamily: mono, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--color-text-secondary)", marginBottom: 6 }}>{label}</div>
		<div style={{ position: "relative", background: "var(--color-bg-section)", border: "1px solid var(--color-border)", borderRadius: 8 }}>
			<pre style={{ margin: 0, padding: "12px 44px 12px 14px", fontFamily: mono, fontSize: 12.5, color: "var(--color-text-primary)", whiteSpace: "pre-wrap", wordBreak: "break-all", overflowX: "auto" }}>{code}</pre>
			<button
				onClick={() => onCopy(code)}
				title="Copy"
				style={{ position: "absolute", top: 8, right: 8, background: "transparent", border: "1px solid var(--color-border)", borderRadius: 6, color: "var(--color-text-secondary)", cursor: "pointer", padding: "3px 8px" }}>
				<i className="bi bi-clipboard"></i>
			</button>
		</div>
	</div>
);

interface Props {
	show: boolean;
	onHide: () => void;
}

const ConnectMcpPanel: React.FC<Props> = ({ show, onHide }) => {
	const { showToast } = useToast();
	const [token, setToken] = useState<string>("");
	const [loading, setLoading] = useState(false);
	const uid = localStorage.getItem("uid") || "";

	useEffect(() => {
		if (!show) return;
		let cancelled = false;
		(async () => {
			try {
				setLoading(true);
				const data = await fetchBillingOverview(uid);
				if (!cancelled) setToken(data?.mcp_token || "");
			} catch {
				/* token stays empty; snippets show a placeholder */
			} finally {
				if (!cancelled) setLoading(false);
			}
		})();
		return () => { cancelled = true; };
	}, [show, uid]);

	const copy = (text: string) => {
		navigator.clipboard.writeText(text);
		showToast("Copied to clipboard", "success");
	};

	const handleRegenerate = async () => {
		if (!window.confirm("Rotate your MCP token? Existing connections using the old token will stop working until you update them.")) return;
		try {
			setLoading(true);
			const data = await regenerateMcpToken();
			setToken(data?.mcp_token || "");
			showToast("MCP token rotated", "success");
		} catch {
			showToast("Could not rotate token", "danger");
		} finally {
			setLoading(false);
		}
	};

	const T = token || "YOUR_TOKEN";
	const cliSnippet = `claude mcp add --transport http waveassist ${MCP_URL} \\\n  --header "Authorization: Bearer ${T}"`;
	const pluginSnippet = `/plugin marketplace add ${MCP_MARKETPLACE}\n/plugin install waveassist@waveassist-marketplace\n/reload-plugins`;
	const cursorSnippet = `{\n  "mcpServers": {\n    "waveassist": {\n      "url": "${MCP_URL}",\n      "headers": { "Authorization": "Bearer ${T}" }\n    }\n  }\n}`;

	return (
		<Modal show={show} onHide={onHide} size="lg" centered>
			<Modal.Header closeButton>
				<Modal.Title style={{ fontFamily: mono, fontWeight: 600 }}>
					<span style={{ color: "var(--color-primary)" }}>/</span>connect over MCP
				</Modal.Title>
			</Modal.Header>
			<Modal.Body>
				<p style={{ color: "var(--color-text-secondary)", marginTop: 0 }}>
					Build &amp; deploy assistants from your editor. Add WaveAssist as an MCP server, then describe what you want. It appears here once deployed.
				</p>

				{/* Identity */}
				<div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 18 }}>
					<div style={{ flex: "1 1 220px", background: "var(--color-bg-card)", border: "1px solid var(--color-border)", borderRadius: 8, padding: "10px 14px" }}>
						<div style={{ fontFamily: mono, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--color-text-secondary)" }}>User ID</div>
						<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 4 }}>
							<span style={{ fontFamily: mono, fontSize: 13, color: "var(--color-text-primary)", wordBreak: "break-all" }}>{uid}</span>
							<button onClick={() => copy(uid)} title="Copy" style={{ background: "transparent", border: "1px solid var(--color-border)", borderRadius: 6, color: "var(--color-text-secondary)", cursor: "pointer", padding: "2px 7px" }}><i className="bi bi-clipboard"></i></button>
						</div>
					</div>
					<div style={{ flex: "1 1 220px", background: "var(--color-bg-card)", border: "1px solid var(--color-border)", borderRadius: 8, padding: "10px 14px" }}>
						<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
							<div style={{ fontFamily: mono, fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--color-text-secondary)" }}>MCP Token</div>
							<button onClick={handleRegenerate} disabled={loading} title="Rotate token" style={{ background: "transparent", border: "none", color: "var(--color-primary)", cursor: "pointer", fontSize: 11, fontFamily: mono }}>
								<i className="bi bi-arrow-repeat"></i> regenerate
							</button>
						</div>
						<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginTop: 4 }}>
							<span style={{ fontFamily: mono, fontSize: 13, color: token ? "var(--color-text-primary)" : "var(--color-text-secondary)", wordBreak: "break-all" }}>{loading ? "…" : token || "click ‘regenerate’ to create a token"}</span>
							{token && <button onClick={() => copy(token)} title="Copy" style={{ background: "transparent", border: "1px solid var(--color-border)", borderRadius: 6, color: "var(--color-text-secondary)", cursor: "pointer", padding: "2px 7px" }}><i className="bi bi-clipboard"></i></button>}
						</div>
					</div>
				</div>

				<CodeBlock label="Claude Code: CLI one-liner" code={cliSnippet} onCopy={copy} />
				<CodeBlock label="Claude Code: plugin" code={pluginSnippet} onCopy={copy} />
				<CodeBlock label="Cursor / any MCP host: ~/.cursor/mcp.json" code={cursorSnippet} onCopy={copy} />
			</Modal.Body>
		</Modal>
	);
};

export default ConnectMcpPanel;

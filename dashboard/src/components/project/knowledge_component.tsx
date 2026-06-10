import React, { useEffect, useState, useCallback } from "react";
import { fetchDataForKeyAPI } from "../../services/project_services";
import { useRefresh } from "../../utils/RefreshContext";
import "./project_components.css";

// The Knowledge tab renders the assistant's "brain" — the structured per-repo profiles a
// node builds about your repositories — natively in React (design-system dark theme,
// independently collapsible cards). Primary source is the consolidated `brain` JSON key;
// if a deployment predates it, we fall back to the per-repo `profile:{repo}` keys.

const ACCENT = "#1ED66C";
const BORDER = "1px solid #2D313A";
const TEXT = "#FFFFFF";
const MUTED = "#A1A1AA";
const BODY = "#D4D4D8";
const CODE_BG = "rgba(255,255,255,0.06)";

interface RepoEntry {
	repo: string;
	profile: any;
}

const formatDate = (iso: string): string => {
	if (!iso) return "";
	const d = new Date(iso);
	if (isNaN(d.getTime())) return "";
	return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
};

const extract = (profile: any) => {
	const stack = profile?.stack || {};
	const tech = [
		...(stack.languages || []),
		...(stack.frameworks || []),
		...(stack.datastores || []),
		...(stack.infrastructure || []),
	].slice(0, 16);
	const deps = profile?.dependencies || [];
	const sec = profile?.security || {};
	const routes = sec.routes || [];
	return {
		summary: profile?.architecture_summary || "",
		tech,
		deps,
		depsAuth: deps.filter((d: any) => d?.in_auth_path),
		routes,
		openRoutes: routes.filter((r: any) => r?.unauthenticated),
		secretSites: sec.secret_locations || [],
		keyFiles: profile?.key_files || [],
		components: profile?.components || [],
		conventions: profile?.conventions || [],
		fp: profile?._fingerprint || {},
	};
};

const Chip: React.FC<{ children: React.ReactNode }> = ({ children }) => (
	<span
		style={{
			display: "inline-block",
			fontSize: 12,
			background: "rgba(255,255,255,0.05)",
			color: BODY,
			border: BORDER,
			borderRadius: 999,
			padding: "3px 12px",
			margin: "0 8px 8px 0",
		}}>
		{children}
	</span>
);

const Stat: React.FC<{ value: number; label: string; danger?: boolean }> = ({ value, label, danger }) => (
	<span style={{ marginRight: 24, color: MUTED, fontSize: 13 }}>
		<b style={{ color: danger && value > 0 ? "#F87171" : ACCENT, fontSize: 15, fontWeight: 600 }}>{value}</b>{" "}
		{label}
	</span>
);

const SectionList: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
	<div style={{ marginTop: 24 }}>
		<div
			style={{
				fontSize: 11,
				fontWeight: 600,
				textTransform: "uppercase",
				letterSpacing: "0.08em",
				color: MUTED,
				marginBottom: 10,
			}}>
			{title}
		</div>
		{children}
	</div>
);

const Code: React.FC<{ children: React.ReactNode }> = ({ children }) => (
	<code style={{ background: CODE_BG, padding: "2px 7px", borderRadius: 5, color: "#A7F3D0", fontSize: 12.5 }}>
		{children}
	</code>
);

const listStyle: React.CSSProperties = {
	margin: "0 0 0 18px",
	color: BODY,
	fontSize: 13.5,
	lineHeight: 1.6,
};

const RepoCard: React.FC<{ entry: RepoEntry; open: boolean; onToggle: () => void }> = ({ entry, open, onToggle }) => {
	const p = extract(entry.profile);
	return (
		<div className="knowledge-card">
			{/* Header — always visible, click to expand */}
			<div className="knowledge-card-header" onClick={onToggle}>
				<i className={`bi bi-chevron-right knowledge-chevron ${open ? "open" : ""}`}></i>
				<span style={{ color: TEXT, fontWeight: 600, fontSize: 15, letterSpacing: "-0.02em" }}>{entry.repo}</span>
				{p.fp.branch && (
					<span
						style={{
							fontSize: 11,
							color: ACCENT,
							background: "rgba(30,214,108,0.12)",
							padding: "3px 10px",
							borderRadius: 10,
						}}>
						{p.fp.branch}
					</span>
				)}
				<span style={{ marginLeft: "auto", color: MUTED, fontSize: 12.5, whiteSpace: "nowrap" }}>
					{p.deps.length} deps ·{" "}
					<span style={{ color: p.openRoutes.length ? "#F87171" : MUTED }}>{p.openRoutes.length} public</span>
				</span>
			</div>

			{/* Body — collapsible */}
			{open && (
				<div style={{ padding: "20px 24px 24px", borderTop: BORDER }}>
					{p.summary && (
						<p style={{ color: BODY, fontSize: 14, lineHeight: 1.65, margin: "0 0 18px" }}>{p.summary}</p>
					)}

					{p.tech.length > 0 && (
						<div style={{ marginBottom: 14 }}>
							{p.tech.map((t: string, i: number) => (
								<Chip key={i}>{t}</Chip>
							))}
						</div>
					)}

					<div style={{ display: "flex", flexWrap: "wrap", rowGap: 8 }}>
						<Stat value={p.deps.length} label="deps" />
						<Stat value={p.depsAuth.length} label="in auth path" />
						<Stat value={p.openRoutes.length} label="public routes" danger />
						<Stat value={p.secretSites.length} label="secret sites" />
					</div>

					{p.keyFiles.length > 0 && (
						<SectionList title="Key files">
							<ul style={listStyle}>
								{p.keyFiles.slice(0, 10).map((k: any, i: number) => (
									<li key={i} style={{ margin: "6px 0" }}>
										<Code>{k.path}</Code> — {k.role}
									</li>
								))}
							</ul>
						</SectionList>
					)}

					{p.components.length > 0 && (
						<SectionList title="Components">
							<ul style={listStyle}>
								{p.components.slice(0, 8).map((c: any, i: number) => (
									<li key={i} style={{ margin: "6px 0" }}>
										<b style={{ color: TEXT, fontWeight: 600 }}>{c.name}</b> — {c.responsibility}
									</li>
								))}
							</ul>
						</SectionList>
					)}

					{p.conventions.length > 0 && (
						<SectionList title="Conventions">
							<ul style={listStyle}>
								{p.conventions.slice(0, 8).map((c: string, i: number) => (
									<li key={i} style={{ margin: "6px 0" }}>
										{c}
									</li>
								))}
							</ul>
						</SectionList>
					)}

					{p.routes.length > 0 && (
						<SectionList title="Routes">
							<ul style={{ ...listStyle, listStyle: "none", margin: 0, paddingLeft: 0 }}>
								{p.routes.slice(0, 12).map((r: any, i: number) => (
									<li key={i} style={{ margin: "6px 0" }}>
										<Code>{r.route}</Code>{" "}
										<span
											style={{
												fontSize: 11,
												fontWeight: 700,
												marginLeft: 4,
												color: r.unauthenticated ? "#F87171" : ACCENT,
											}}>
											{r.unauthenticated ? "PUBLIC" : "auth"}
										</span>
									</li>
								))}
							</ul>
						</SectionList>
					)}

					{p.fp.sha && (
						<div style={{ marginTop: 24, paddingTop: 14, borderTop: BORDER, fontSize: 11, color: MUTED }}>
							fingerprint {String(p.fp.sha).slice(0, 10)} · built {formatDate(p.fp.built_at)}
						</div>
					)}
				</div>
			)}
		</div>
	);
};

const KnowledgeComponent: React.FC = () => {
	const [repos, setRepos] = useState<RepoEntry[]>([]);
	const [builtAt, setBuiltAt] = useState<string>("");
	const [isLoading, setIsLoading] = useState(true);
	// Each card toggles independently (no auto-collapse of others — collapsing a tall card
	// above the one you clicked makes the page jump). First card starts open.
	const [openRepos, setOpenRepos] = useState<Set<string>>(new Set());
	const { shouldRefresh } = useRefresh();

	const fetchBrain = useCallback(async () => {
		setIsLoading(true);
		try {
			// Primary: consolidated `brain` JSON.
			const resp = await fetchDataForKeyAPI("brain");
			const brain = resp?.data;
			if (brain?.repos?.length) {
				setRepos(brain.repos);
				setBuiltAt(brain.built_at || "");
				setOpenRepos(new Set([brain.repos[0].repo]));
				return;
			}
			throw new Error("no consolidated brain");
		} catch {
			// Fallback: build from the per-repo profile keys (older deployments).
			try {
				const groupsResp = await fetchDataForKeyAPI("repo_groups");
				const groups = groupsResp?.data || {};
				const names = Object.keys(groups);
				const profiles = await Promise.all(
					names.map((r) =>
						fetchDataForKeyAPI(`profile:${r}`)
							.then((pr) => ({ repo: r, profile: pr?.data }))
							.catch(() => null)
					)
				);
				const entries = profiles.filter(
					(e): e is RepoEntry => !!e && e.profile?.schema_version === "repo_context_profile_v2"
				);
				setRepos(entries);
				if (entries.length) setOpenRepos(new Set([entries[0].repo]));
				const dates = entries.map((e) => e.profile?._fingerprint?.built_at).filter(Boolean) as string[];
				setBuiltAt(dates.sort().slice(-1)[0] || "");
			} catch {
				setRepos([]);
			}
		} finally {
			setIsLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchBrain();
	}, [fetchBrain, shouldRefresh]);

	const toggleRepo = (repo: string) => {
		setOpenRepos((prev) => {
			const next = new Set(prev);
			if (next.has(repo)) next.delete(repo);
			else next.add(repo);
			return next;
		});
	};

	return (
		<div className="main-container">
			<div className="mt-3 d-flex flex-column" style={{ height: "100%" }}>
				<div style={{ flex: "0 0 100%", display: "flex", flexDirection: "column" }}>
					<div className="d-flex justify-content-between align-items-center mb-4">
						<h3 className="translucent_white">Knowledge</h3>
						{repos.length > 0 && (
							<span style={{ display: "inline-flex", alignItems: "center", gap: 8, color: MUTED, fontSize: 13 }}>
								<span className="knowledge-live-dot"></span>
								{repos.length} {repos.length === 1 ? "repository" : "repositories"} profiled · auto-updates
								{builtAt && <span> · last updated {formatDate(builtAt)}</span>}
							</span>
						)}
					</div>

					{isLoading ? (
						<div className="d-flex justify-content-center align-items-center" style={{ flex: 1, minHeight: "400px" }}>
							<div className="text-center">
								<div className="spinner-border text-success mb-3" role="status" style={{ width: "3rem", height: "3rem" }}>
									<span className="visually-hidden">Loading...</span>
								</div>
								<div className="text-white">Loading knowledge...</div>
							</div>
						</div>
					) : repos.length > 0 ? (
						<div style={{ paddingBottom: 24 }}>
							{repos.map((entry) => (
								<RepoCard
									key={entry.repo}
									entry={entry}
									open={openRepos.has(entry.repo)}
									onToggle={() => toggleRepo(entry.repo)}
								/>
							))}
						</div>
					) : (
						<div className="d-flex justify-content-center align-items-center" style={{ flex: 1, minHeight: "400px" }}>
							<div className="text-center" style={{ color: MUTED }}>
								<i className="bi bi-lightbulb" style={{ fontSize: "2.5rem", opacity: 0.5 }}></i>
								<div className="mt-3" style={{ fontWeight: 600, color: TEXT }}>No knowledge yet</div>
								<div className="mt-1" style={{ maxWidth: 420 }}>
									Knowledge appears here if your assistant builds context to better understand your work.
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
};

export default KnowledgeComponent;

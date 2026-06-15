import React, { useEffect, useMemo, useRef, useState } from "react";
import { Form, Button } from "react-bootstrap";
import "./RepoGroupsInput.css";

// Group-builder input for GitZoid's Knowledge Digest. Each group is one weekly digest email over a
// subset of the selected repos, with its own recipients. Membership is exclusive: a repo belongs to at
// most one group. The value is a JSON string of RepoGroup[], stored under the `digest_groups` key; an
// empty value means GitZoid sends a single digest covering all selected repos.

interface RepoGroup {
	name: string;
	repos: string[];
	recipients: string[];
}

interface RepoGroupsInputProps {
	value: string;
	onChange: (value: string) => void;
	// The user's selected GitHub repos, resolved from the `github` integration (depends_on).
	availableRepos?: Array<{ id?: string; name?: string } | string>;
	maxGroups?: number;
}

const MAX_RECIPIENTS = 10;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const repoIdOf = (r: { id?: string; name?: string } | string): string =>
	typeof r === "string" ? r : r?.id || r?.name || "";

const parseGroups = (value: string): RepoGroup[] => {
	if (!value || !value.trim()) {
		return [];
	}
	try {
		const parsed = JSON.parse(value);
		if (Array.isArray(parsed)) {
			return parsed
				.filter((g) => g && typeof g === "object")
				.map((g) => ({
					name: typeof g.name === "string" ? g.name : "",
					repos: Array.isArray(g.repos) ? g.repos.filter((x: unknown) => typeof x === "string") : [],
					recipients: Array.isArray(g.recipients)
						? g.recipients.filter((x: unknown) => typeof x === "string")
						: [],
				}));
		}
	} catch {
		// Malformed value falls back to "no groups" (single implicit digest at runtime).
	}
	return [];
};

const RepoGroupsInput: React.FC<RepoGroupsInputProps> = ({ value, onChange, availableRepos, maxGroups = 10 }) => {
	const groups = useMemo(() => parseGroups(value), [value]);
	const repoIds = useMemo(
		() => (availableRepos || []).map(repoIdOf).filter((id) => id.length > 0),
		[availableRepos]
	);
	const [drafts, setDrafts] = useState<Record<number, string>>({});

	// Auto-seed one group with all selected repos the first time the builder opens with none configured,
	// so a user who just connects GitHub and clicks through still gets a working all-repos digest without
	// having to create a group. Guarded by a ref so deleting every group later does not re-create one.
	const seeded = useRef(false);
	useEffect(() => {
		if (!seeded.current && groups.length === 0 && repoIds.length > 0) {
			seeded.current = true;
			onChange(JSON.stringify([{ name: "All repositories", repos: [...repoIds], recipients: [] }]));
		}
	}, [groups, repoIds, onChange]);

	const commit = (next: RepoGroup[]) => onChange(JSON.stringify(next));

	// repo id -> index of the group that currently owns it (for exclusive membership + "in: X" labels).
	const ownerOf = useMemo(() => {
		const map: Record<string, number> = {};
		groups.forEach((group, i) => group.repos.forEach((repo) => { map[repo] = i; }));
		return map;
	}, [groups]);

	const setDraft = (idx: number, text: string) => setDrafts((prev) => ({ ...prev, [idx]: text }));

	const addGroup = () => {
		if (groups.length >= maxGroups) {
			return;
		}
		// The first group is pre-populated with all selected repos (matches the approved first-run UX);
		// later groups start empty so the user moves repos in deliberately.
		const repos = groups.length === 0 ? [...repoIds] : [];
		commit([...groups, { name: "", repos, recipients: [] }]);
	};

	const removeGroup = (idx: number) => commit(groups.filter((_, i) => i !== idx));

	const setName = (idx: number, name: string) =>
		commit(groups.map((group, i) => (i === idx ? { ...group, name } : group)));

	const toggleRepo = (idx: number, repo: string) => {
		const wasMine = ownerOf[repo] === idx;
		// Remove the repo from every group first (atomic move out of any other group)...
		const next = groups.map((group) => ({ ...group, repos: group.repos.filter((r) => r !== repo) }));
		// ...then add it to this group unless we were just unchecking it.
		if (!wasMine) {
			next[idx] = { ...next[idx], repos: [...next[idx].repos, repo] };
		}
		commit(next);
	};

	const addRecipient = (idx: number) => {
		const draft = (drafts[idx] || "").trim();
		if (!EMAIL_RE.test(draft)) {
			return;
		}
		const group = groups[idx];
		if (group.recipients.includes(draft) || group.recipients.length >= MAX_RECIPIENTS) {
			setDraft(idx, "");
			return;
		}
		commit(groups.map((g, i) => (i === idx ? { ...g, recipients: [...g.recipients, draft] } : g)));
		setDraft(idx, "");
	};

	const removeRecipient = (idx: number, email: string) =>
		commit(groups.map((g, i) => (i === idx ? { ...g, recipients: g.recipients.filter((e) => e !== email) } : g)));

	if (repoIds.length === 0) {
		return (
			<div className="repo-groups-empty">
				Select the repositories you want to monitor above, then group them here for the weekly digest.
			</div>
		);
	}

	return (
		<div className="repo-groups">
			{groups.length === 0 && (
				<div className="repo-groups-empty">
					No groups yet. GitZoid will send one digest covering all selected repos. Create a group to
					split them into separate project digests with their own recipients.
				</div>
			)}

			{groups.map((group, idx) => {
				const draftEmail = drafts[idx] || "";
				const draftInvalid = draftEmail.trim().length > 0 && !EMAIL_RE.test(draftEmail.trim());
				return (
					<div className="repo-group-card" key={idx}>
						<div className="repo-group-header">
							<Form.Control
								className="repo-group-name"
								type="text"
								value={group.name}
								placeholder="Project name (e.g. Platform)"
								onChange={(e) => setName(idx, e.target.value)}
							/>
							<button
								type="button"
								className="repo-group-remove"
								onClick={() => removeGroup(idx)}
								aria-label="Remove group">
								Remove
							</button>
						</div>

						<div className="repo-group-label">Repositories</div>
						<div className="repo-group-repos">
							{repoIds.map((repo) => {
								const owner = ownerOf[repo];
								const inThisGroup = owner === idx;
								const inOtherGroup = owner !== undefined && owner !== idx;
								return (
									<label
										key={repo}
										className={`repo-checkbox${inOtherGroup ? " repo-checkbox-disabled" : ""}`}
										title={inOtherGroup ? `Already in: ${groups[owner].name || "Untitled group"}` : undefined}>
										<input
											type="checkbox"
											checked={inThisGroup}
											disabled={inOtherGroup}
											onChange={() => toggleRepo(idx, repo)}
										/>
										<span className="repo-checkbox-name">{repo}</span>
										{inOtherGroup && (
											<span className="repo-checkbox-tag">in: {groups[owner].name || "Untitled"}</span>
										)}
									</label>
								);
							})}
						</div>

						<div className="repo-group-label">Additional recipients</div>
						<div className="repo-recipients">
							{group.recipients.map((email) => (
								<span className="repo-recipient-chip" key={email}>
									{email}
									<button
										type="button"
										className="repo-recipient-remove"
										onClick={() => removeRecipient(idx, email)}
										aria-label={`Remove ${email}`}>
										×
									</button>
								</span>
							))}
						</div>
						<div className="repo-recipient-add">
							<Form.Control
								type="email"
								value={draftEmail}
								placeholder="email@company.com"
								isInvalid={draftInvalid}
								disabled={group.recipients.length >= MAX_RECIPIENTS}
								onChange={(e) => setDraft(idx, e.target.value)}
								onKeyDown={(e) => {
									if (e.key === "Enter") {
										e.preventDefault();
										addRecipient(idx);
									}
								}}
							/>
							<Button
								className="repo-recipient-btn"
								variant="outline-secondary"
								onClick={() => addRecipient(idx)}
								disabled={!EMAIL_RE.test(draftEmail.trim()) || group.recipients.length >= MAX_RECIPIENTS}>
								Add
							</Button>
						</div>
						<div className="repo-group-hint">
							The account owner always receives this digest. Add extra recipients to CC.
						</div>
					</div>
				);
			})}

			<Button
				className="repo-group-add"
				variant="outline-secondary"
				onClick={addGroup}
				disabled={groups.length >= maxGroups}>
				+ Add group{groups.length >= maxGroups ? ` (max ${maxGroups})` : ""}
			</Button>
		</div>
	);
};

export default RepoGroupsInput;

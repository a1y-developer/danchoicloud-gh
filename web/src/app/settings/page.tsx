"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import styles from "./page.module.css";

type IntegrationScope = {
  scope_type: "org" | "repo" | null;
  scope_name: string | null;
  locked: boolean;
};

type NotificationChannel = {
  id: number;
  scope_type: "org" | "repo";
  scope_name: string;
  channel_type: "telegram" | "discord" | "slack" | "webhook";
  config: Record<string, unknown>;
  is_active: boolean;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const defaultConfigs: Record<string, Record<string, unknown>> = {
  telegram: { bot_token: "", chat_id: "", thread_id: "" },
  slack: { webhook_url: "" },
  discord: { webhook_url: "" },
  webhook: { url: "", method: "POST", headers: {} },
};

export default function SettingsPage() {
  const [scopeType, setScopeType] = useState<"" | "org" | "repo">("");
  const [scopeName, setScopeName] = useState("");
  const [scopeLocked, setScopeLocked] = useState(false);
  const [scopeStatus, setScopeStatus] = useState<string | null>(null);

  const [channelScopeType, setChannelScopeType] = useState<"org" | "repo">("org");
  const [channelScopeName, setChannelScopeName] = useState("");
  const [channelType, setChannelType] = useState<
    "telegram" | "discord" | "slack" | "webhook"
  >("slack");
  const [configText, setConfigText] = useState(
    JSON.stringify(defaultConfigs.slack, null, 2),
  );
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [channelStatus, setChannelStatus] = useState<string | null>(null);

  const configHint = useMemo(
    () => JSON.stringify(defaultConfigs[channelType], null, 2),
    [channelType],
  );

  useEffect(() => {
    setConfigText(JSON.stringify(defaultConfigs[channelType], null, 2));
  }, [channelType]);

  useEffect(() => {
    const loadScope = async () => {
      const response = await fetch(
        `${API_BASE_URL}/api/v1/settings/integration-scope`,
        { credentials: "include" },
      );
      if (!response.ok) {
        return;
      }
      const data = (await response.json()) as IntegrationScope;
      setScopeType((data.scope_type ?? "") as "" | "org" | "repo");
      setScopeName(data.scope_name ?? "");
      setScopeLocked(Boolean(data.locked));
    };

    loadScope();
  }, []);

  const loadChannels = async () => {
    setChannelStatus(null);
    if (!channelScopeName) {
      setChannelStatus("Enter a scope name to load channels.");
      return;
    }
    const params = new URLSearchParams({
      scope_type: channelScopeType,
      scope_name: channelScopeName,
    });
    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/channels?${params.toString()}`,
      { credentials: "include" },
    );
    if (!response.ok) {
      setChannelStatus("Unable to load notification channels.");
      return;
    }
    const data = (await response.json()) as NotificationChannel[];
    setChannels(data);
  };

  const saveScope = async () => {
    setScopeStatus(null);
    const payload = {
      scope_type: scopeType || null,
      scope_name: scopeType ? scopeName : null,
    };
    const response = await fetch(
      `${API_BASE_URL}/api/v1/settings/integration-scope`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      },
    );
    if (!response.ok) {
      setScopeStatus("Unable to save integration scope.");
      return;
    }
    setScopeStatus("Integration scope updated.");
  };

  const createChannel = async () => {
    setChannelStatus(null);
    if (!channelScopeName) {
      setChannelStatus("Scope name is required for notifications.");
      return;
    }
    let parsedConfig: Record<string, unknown> = {};
    try {
      parsedConfig = JSON.parse(configText);
    } catch (err) {
      setChannelStatus("Config must be valid JSON.");
      return;
    }

    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/channels`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          scope_type: channelScopeType,
          scope_name: channelScopeName,
          channel_type: channelType,
          config: parsedConfig,
          is_active: true,
        }),
      },
    );
    if (!response.ok) {
      setChannelStatus("Unable to create notification channel.");
      return;
    }
    await loadChannels();
    setChannelStatus("Channel saved.");
  };

  const toggleChannel = async (channel: NotificationChannel) => {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/channels/${channel.id}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ is_active: !channel.is_active }),
      },
    );
    if (!response.ok) {
      setChannelStatus("Unable to update channel.");
      return;
    }
    await loadChannels();
  };

  const deleteChannel = async (channelId: number) => {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/notifications/channels/${channelId}`,
      { method: "DELETE", credentials: "include" },
    );
    if (!response.ok) {
      setChannelStatus("Unable to delete channel.");
      return;
    }
    await loadChannels();
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link className={styles.backLink} href="/">
          ← Back to home
        </Link>
        <h1>Configuration</h1>
        <p>Set the allowed GitHub scope and manage notification channels.</p>
      </header>

      <section className={styles.card}>
        <h2>Integration scope</h2>
        <p className={styles.muted}>
          Restrict the app to a single organization or repository.
        </p>
        <div className={styles.formRow}>
          <label>
            Scope type
            <select
              value={scopeType}
              disabled={scopeLocked}
              onChange={(event) =>
                setScopeType(event.target.value as "" | "org" | "repo")
              }
            >
              <option value="">None</option>
              <option value="org">Organization</option>
              <option value="repo">Repository</option>
            </select>
          </label>
          <label>
            Scope name
            <input
              value={scopeName}
              disabled={scopeLocked || !scopeType}
              placeholder={scopeType === "repo" ? "org/repo" : "org-name"}
              onChange={(event) => setScopeName(event.target.value)}
            />
          </label>
        </div>
        {scopeLocked ? (
          <p className={styles.notice}>
            Integration scope is locked via environment settings.
          </p>
        ) : (
          <button className={styles.primary} onClick={saveScope} type="button">
            Save scope
          </button>
        )}
        {scopeStatus ? <p className={styles.status}>{scopeStatus}</p> : null}
      </section>

      <section className={styles.card}>
        <h2>Notification channels</h2>
        <p className={styles.muted}>
          Configure Telegram, Slack, Discord, or webhook destinations by scope.
        </p>
        <div className={styles.formRow}>
          <label>
            Scope type
            <select
              value={channelScopeType}
              onChange={(event) =>
                setChannelScopeType(event.target.value as "org" | "repo")
              }
            >
              <option value="org">Organization</option>
              <option value="repo">Repository</option>
            </select>
          </label>
          <label>
            Scope name
            <input
              value={channelScopeName}
              placeholder={
                channelScopeType === "repo" ? "org/repo" : "org-name"
              }
              onChange={(event) => setChannelScopeName(event.target.value)}
            />
          </label>
          <button className={styles.secondary} onClick={loadChannels} type="button">
            Load channels
          </button>
        </div>

        <div className={styles.formRow}>
          <label>
            Channel type
            <select
              value={channelType}
              onChange={(event) =>
                setChannelType(
                  event.target.value as
                    | "telegram"
                    | "discord"
                    | "slack"
                    | "webhook",
                )
              }
            >
              <option value="slack">Slack</option>
              <option value="discord">Discord</option>
              <option value="telegram">Telegram</option>
              <option value="webhook">Webhook</option>
            </select>
          </label>
          <label className={styles.fullWidth}>
            Config (JSON)
            <textarea
              value={configText}
              placeholder={configHint}
              onChange={(event) => setConfigText(event.target.value)}
              rows={6}
            />
          </label>
        </div>
        <button className={styles.primary} onClick={createChannel} type="button">
          Save channel
        </button>
        {channelStatus ? <p className={styles.status}>{channelStatus}</p> : null}

        <div className={styles.channelList}>
          {channels.map((channel) => (
            <div key={channel.id} className={styles.channelItem}>
              <div>
                <p className={styles.channelTitle}>
                  {channel.channel_type.toUpperCase()} · {channel.scope_type} ·{" "}
                  {channel.scope_name}
                </p>
                <p className={styles.muted}>
                  {channel.is_active ? "Active" : "Disabled"}
                </p>
              </div>
              <div className={styles.channelActions}>
                <button
                  className={styles.secondary}
                  onClick={() => toggleChannel(channel)}
                  type="button"
                >
                  {channel.is_active ? "Disable" : "Enable"}
                </button>
                <button
                  className={styles.danger}
                  onClick={() => deleteChannel(channel.id)}
                  type="button"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
          {channels.length === 0 ? (
            <p className={styles.muted}>No channels configured yet.</p>
          ) : null}
        </div>
      </section>
    </div>
  );
}

"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";

import styles from "./page.module.css";

type SessionUser = {
  login: string;
  name?: string | null;
  avatar_url?: string | null;
};

type SessionResponse = {
  authenticated: boolean;
  user: SessionUser | null;
  app_slug?: string | null;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const DEFAULT_APP_SLUG = process.env.NEXT_PUBLIC_GITHUB_APP_SLUG ?? "";

export default function Home() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSession = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/session`, {
          credentials: "include",
        });
        if (!response.ok) {
          setSession({ authenticated: false, user: null });
          return;
        }
        const data = (await response.json()) as SessionResponse;
        setSession(data);
      } catch {
        setError("Unable to reach the API. Check your backend URL.");
        setSession({ authenticated: false, user: null });
      }
    };

    loadSession();
  }, []);

  const loginUrl = `${API_BASE_URL}/api/v1/auth/github/authorize`;
  const appSlug = session?.app_slug || DEFAULT_APP_SLUG;
  const installUrl = appSlug
    ? `https://github.com/apps/${appSlug}/installations/new`
    : null;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>Danchoicloud GitHub App</p>
          <h1>Connect your GitHub organizations and repositories.</h1>
          <p className={styles.subtitle}>
            Log in with GitHub to install the app, set integration scope, and
            configure notification channels.
          </p>
        </div>
      </header>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <h2>Login status</h2>
          <p>Authenticate to manage installations and notifications.</p>
        </div>
        {error ? <p className={styles.error}>{error}</p> : null}
        {session?.authenticated && session.user ? (
          <div className={styles.userRow}>
            {session.user.avatar_url ? (
              <Image
                className={styles.avatar}
                src={session.user.avatar_url}
                alt={`${session.user.login} avatar`}
                width={56}
                height={56}
              />
            ) : null}
            <div>
              <p className={styles.userName}>
                {session.user.name || session.user.login}
              </p>
              <p className={styles.userLogin}>@{session.user.login}</p>
            </div>
          </div>
        ) : (
          <p className={styles.muted}>You are not signed in.</p>
        )}
        <div className={styles.actions}>
          <a className={styles.primary} href={loginUrl}>
            Sign in with GitHub
          </a>
          {installUrl ? (
            <a
              className={styles.secondary}
              href={installUrl}
              target="_blank"
              rel="noreferrer"
            >
              Install GitHub App
            </a>
          ) : (
            <span className={styles.disabled}>App slug not configured</span>
          )}
          <Link className={styles.link} href="/settings">
            Configure notifications →
          </Link>
        </div>
      </section>
    </div>
  );
}

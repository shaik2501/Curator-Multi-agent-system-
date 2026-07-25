"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { Icon } from "@/components/ui/icon";
import { CopyButton } from "@/components/ui/copy-button";
import { useConfirm } from "@/components/ui/confirm-dialog";
import {
  ApiError,
  checkOllama,
  createLLMConfig,
  deleteLLMConfig,
  getSettings,
  listModels,
  verifyLLMConfig,
} from "@/lib/api";
import { useLLMConfigs } from "@/lib/use-llm-configs";
import {
  PROVIDER_CHEAP_MODEL_PLACEHOLDER,
  PROVIDER_KEYS,
  PROVIDER_META,
  PROVIDER_MODEL_PLACEHOLDER,
} from "@/lib/types";
import type { LLMConfig, Provider, SettingsResponse } from "@/lib/types";

const OLLAMA_MODELS = ["llama3.1:8b", "qwen2.5:7b", "mistral"];

function OllamaSetupPanel() {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<"reachable" | "unreachable" | "unavailable" | null>(null);

  const testConnection = async () => {
    setChecking(true);
    setResult(null);
    try {
      const res = await checkOllama();
      setResult(res.reachable ? "reachable" : "unreachable");
    } catch (err) {
      setResult(err instanceof ApiError && err.status === 404 ? "unavailable" : "unreachable");
    } finally {
      setChecking(false);
    }
  };

  return (
    <section className="glass-panel rounded-2xl border border-primary/20 p-6">
      <div className="mb-4 flex items-center gap-2">
        <Icon name="terminal" className="text-primary" />
        <h3 className="font-headline-sm text-headline-sm text-on-surface">
          Set up a local model
        </h3>
      </div>
      <p className="mb-4 text-sm text-on-surface-variant">
        Ollama runs models on your own machine — free, private, and works
        offline. Follow these steps, then add it below as an LLM config with
        provider type <strong>Ollama</strong> to select it on the dashboard.
        (The backend also auto-seeds an env-based Ollama config by default —
        this is additive for anyone who wants ad-hoc/extra local setups.)
      </p>

      <ol className="flex flex-col gap-4">
        <li className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-container text-xs font-bold text-primary">
            1
          </span>
          <p className="text-sm text-on-surface">
            Install Ollama from{" "}
            <a
              href="https://ollama.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              ollama.com
            </a>
            .
          </p>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-container text-xs font-bold text-primary">
            2
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm text-on-surface">
              Ollama usually starts automatically after install. If it doesn&apos;t,
              start it manually:
            </p>
            <div className="mt-1.5 flex items-center justify-between gap-2 rounded-lg bg-surface-container-lowest px-3 py-2">
              <code className="font-code-sm text-code-sm text-on-surface">ollama serve</code>
              <CopyButton text="ollama serve" />
            </div>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-container text-xs font-bold text-primary">
            3
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm text-on-surface">
              Pull a model — whichever you choose is the one you&apos;ll enter as
              the Model field below:
            </p>
            <div className="mt-1.5 flex flex-col gap-1.5">
              {OLLAMA_MODELS.map((m) => (
                <div
                  key={m}
                  className="flex items-center justify-between gap-2 rounded-lg bg-surface-container-lowest px-3 py-2"
                >
                  <code className="font-code-sm text-code-sm text-on-surface">
                    ollama pull {m}
                  </code>
                  <CopyButton text={`ollama pull ${m}`} />
                </div>
              ))}
            </div>
          </div>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-container text-xs font-bold text-primary">
            4
          </span>
          <p className="text-sm text-on-surface">
            The default base URL <code className="font-code-sm text-code-sm">http://localhost:11434</code>{" "}
            is already correct for a standard local install — no change
            usually needed.
          </p>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-container text-xs font-bold text-primary">
            5
          </span>
          <p className="text-sm text-on-surface">
            Add it below with the &ldquo;Add an LLM&rdquo; form (provider type
            Ollama) — no restart needed for a config you add this way.
          </p>
        </li>
        <li className="flex gap-3">
          <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-container text-xs font-bold text-primary">
            6
          </span>
          <div className="min-w-0 flex-1">
            <p className="mb-2 text-sm text-on-surface">
              Or just test connectivity right here, independent of any saved
              config:
            </p>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={testConnection}
                disabled={checking}
                className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                <Icon name={checking ? "sync" : "wifi_tethering"} className="text-[16px]" />
                {checking ? "Checking…" : "Test Connection"}
              </button>
              {result === "reachable" && (
                <span className="flex items-center gap-1 text-sm font-semibold text-emerald-400">
                  <Icon name="check_circle" filled className="text-[16px]" />
                  Reachable
                </span>
              )}
              {result === "unreachable" && (
                <span className="flex items-center gap-1 text-sm font-semibold text-error">
                  <Icon name="cancel" className="text-[16px]" />
                  Not reachable
                </span>
              )}
              {result === "unavailable" && (
                <span className="text-sm text-warn">
                  This check isn&apos;t deployed on the backend yet.
                </span>
              )}
            </div>
          </div>
        </li>
      </ol>
    </section>
  );
}

function AddLLMForm({ onCreated }: { onCreated: (config: LLMConfig) => void }) {
  const [providerType, setProviderType] = useState<Provider>("claude");
  const [label, setLabel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("http://localhost:11434");
  const [model, setModel] = useState("");
  const [cheapModel, setCheapModel] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [imageCapable, setImageCapable] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<
    { ok: true; config: LLMConfig } | { ok: false; message: string } | null
  >(null);

  // Live model list, fetched on demand — never guessed/prefilled.
  const [modelList, setModelList] = useState<string[] | null>(null);
  const [fetchingModels, setFetchingModels] = useState(false);
  const [modelFetchError, setModelFetchError] = useState<string | null>(null);
  const [modelManualEntry, setModelManualEntry] = useState(false);
  const [cheapModelManualEntry, setCheapModelManualEntry] = useState(false);

  const resetModelList = () => {
    setModelList(null);
    setModelFetchError(null);
    setModelManualEntry(false);
    setCheapModelManualEntry(false);
  };

  const changeProviderType = (next: Provider) => {
    setProviderType(next);
    setModel("");
    setCheapModel("");
    setBaseUrl(next === "ollama" ? "http://localhost:11434" : "");
    setImageCapable(false);
    setResult(null);
    resetModelList();
  };

  const needsKey = providerType !== "ollama";
  const needsBaseUrl = providerType === "custom";
  const showsBaseUrl = providerType === "custom" || providerType === "ollama";

  // The Fetch button only needs whatever this provider type requires to
  // attempt a lookup — a key for claude/openai/gemini, a base URL for
  // custom (ollama already has a usable default prefilled).
  const canFetchModels = needsKey ? Boolean(apiKey.trim()) : !needsBaseUrl || Boolean(baseUrl.trim());

  const fetchModels = async () => {
    setFetchingModels(true);
    setModelFetchError(null);
    setModelList(null);
    try {
      const res = await listModels({
        provider_type: providerType,
        api_key: apiKey.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
      });
      if (res.models.length > 0) {
        setModelList(res.models);
        setModel(res.models[0]);
        setCheapModel(res.models[0]);
        setModelManualEntry(false);
        setCheapModelManualEntry(false);
      } else {
        setModelList([]);
        setModelFetchError(
          res.error ||
            "This endpoint didn't return any models — enter the model name manually.",
        );
      }
    } catch (err) {
      setModelFetchError(
        err instanceof ApiError
          ? err.message
          : "Could not reach the backend to list models.",
      );
    } finally {
      setFetchingModels(false);
    }
  };

  const submit = async () => {
    if (!model.trim()) return;
    if (needsBaseUrl && !baseUrl.trim()) return;
    setSaving(true);
    setResult(null);
    try {
      const config = await createLLMConfig({
        label: label.trim() || undefined,
        provider_type: providerType,
        api_key: apiKey.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
        model: model.trim(),
        cheap_model: cheapModel.trim() || undefined,
        // Only meaningful for custom — claude/openai/gemini/ollama are
        // determined server-side and this is ignored for them.
        image_capable: providerType === "custom" ? imageCapable : undefined,
      });
      setResult({ ok: true, config });
      onCreated(config);
      // Reset the light fields but keep provider type so the user can
      // immediately see the result against what they just chose.
      setLabel("");
      setApiKey("");
    } catch (err) {
      setResult({
        ok: false,
        message:
          err instanceof ApiError
            ? err.message
            : "Could not reach the backend to save this config.",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="glass-panel rounded-2xl p-6">
      <h3 className="mb-1 font-headline-sm text-headline-sm text-on-surface">Add an LLM</h3>
      <p className="mb-4 text-sm text-on-surface-variant">
        Paste a key, save, and it&apos;s verified live — you can select it on
        the dashboard right after.
      </p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-on-surface-variant">Provider type</span>
          <select
            value={providerType}
            onChange={(e) => changeProviderType(e.target.value as Provider)}
            className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface focus:border-primary focus:outline-none"
          >
            {PROVIDER_KEYS.map((p) => (
              <option key={p} value={p}>
                {PROVIDER_META[p].label}
                {(p === "openai" || p === "gemini") && " 🖼️ image-capable"}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-on-surface-variant">Label (optional)</span>
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. My OpenAI Key"
            className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:border-primary focus:outline-none"
          />
        </label>

        {needsKey && (
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-xs font-medium text-on-surface-variant">API key</span>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-…"
              autoComplete="off"
              className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 font-code-sm text-code-sm text-on-surface placeholder:text-on-surface-variant/40 focus:border-primary focus:outline-none"
            />
          </label>
        )}

        {showsBaseUrl && (
          <label className="flex flex-col gap-1.5 sm:col-span-2">
            <span className="text-xs font-medium text-on-surface-variant">
              Base URL {needsBaseUrl ? "" : "(optional)"}
            </span>
            <input
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={
                providerType === "custom"
                  ? "https://api.example.com/v1"
                  : "http://localhost:11434"
              }
              className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 font-code-sm text-code-sm text-on-surface placeholder:text-on-surface-variant/40 focus:border-primary focus:outline-none"
            />
            {providerType === "custom" && (
              <span className="text-[11px] text-on-surface-variant/70">
                Any OpenAI-compatible endpoint — OpenRouter, Groq, Together, LM Studio, vLLM, etc.
              </span>
            )}
          </label>
        )}

        {providerType === "custom" && (
          <label className="flex items-center gap-2 text-xs text-on-surface-variant sm:col-span-2">
            <input
              type="checkbox"
              checked={imageCapable}
              onChange={(e) => setImageCapable(e.target.checked)}
              className="h-4 w-4 rounded border-outline-variant/30 accent-primary"
            />
            This endpoint supports image generation
          </label>
        )}

        <div className="flex flex-col gap-1.5 sm:col-span-2">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={fetchModels}
              disabled={!canFetchModels || fetchingModels}
              className="flex items-center gap-2 rounded-lg border border-outline-variant/30 bg-surface-container-high px-3 py-1.5 text-xs font-medium text-on-surface transition-colors hover:bg-surface-variant/30 disabled:opacity-50"
            >
              <Icon
                name={fetchingModels ? "sync" : "travel_explore"}
                className={`text-[14px] ${fetchingModels ? "animate-spin" : ""}`}
              />
              {fetchingModels ? "Fetching…" : "Fetch available models"}
            </button>
            {modelFetchError && (
              <span className="text-xs text-warn">{modelFetchError}</span>
            )}
          </div>
        </div>

        <label className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-on-surface-variant">Model</span>
            {modelList && modelList.length > 0 && (
              <button
                type="button"
                onClick={() => setModelManualEntry((v) => !v)}
                className="text-[11px] text-primary hover:underline"
              >
                {modelManualEntry ? "choose from list" : "enter manually instead"}
              </button>
            )}
          </div>
          {modelList && modelList.length > 0 && !modelManualEntry ? (
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 font-code-sm text-code-sm text-on-surface focus:border-primary focus:outline-none"
            >
              {modelList.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={PROVIDER_MODEL_PLACEHOLDER[providerType]}
              className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 font-code-sm text-code-sm text-on-surface placeholder:text-on-surface-variant/40 focus:border-primary focus:outline-none"
            />
          )}
        </label>
      </div>

      <button
        type="button"
        onClick={() => setShowAdvanced((v) => !v)}
        className="mt-3 flex items-center gap-1 text-xs text-on-surface-variant hover:text-on-surface"
      >
        <Icon name={showAdvanced ? "expand_less" : "expand_more"} className="text-[16px]" />
        Advanced: cheap model
      </button>
      {showAdvanced && (
        <div className="mt-2 flex flex-col gap-1.5 sm:w-1/2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-on-surface-variant">
              Cheap model (optional — used for lightweight steps)
            </span>
            {modelList && modelList.length > 0 && (
              <button
                type="button"
                onClick={() => setCheapModelManualEntry((v) => !v)}
                className="text-[11px] text-primary hover:underline"
              >
                {cheapModelManualEntry ? "choose from list" : "enter manually instead"}
              </button>
            )}
          </div>
          {modelList && modelList.length > 0 && !cheapModelManualEntry ? (
            <select
              value={cheapModel}
              onChange={(e) => setCheapModel(e.target.value)}
              className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 font-code-sm text-code-sm text-on-surface focus:border-primary focus:outline-none"
            >
              {modelList.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          ) : (
            <input
              value={cheapModel}
              onChange={(e) => setCheapModel(e.target.value)}
              placeholder={PROVIDER_CHEAP_MODEL_PLACEHOLDER[providerType]}
              className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 font-code-sm text-code-sm text-on-surface placeholder:text-on-surface-variant/40 focus:border-primary focus:outline-none"
            />
          )}
        </div>
      )}

      <div className="mt-4 flex items-center gap-3">
        <button
          type="button"
          onClick={submit}
          disabled={saving || !model.trim() || (needsBaseUrl && !baseUrl.trim())}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          <Icon name={saving ? "sync" : "add_circle"} className="text-[16px]" />
          {saving ? "Saving & verifying…" : "Save & Verify"}
        </button>
        {result?.ok && result.config.status === "verified" && (
          <span className="flex items-center gap-1 text-sm font-semibold text-emerald-400">
            <Icon name="check_circle" filled className="text-[16px]" />
            Verified
          </span>
        )}
        {result?.ok && result.config.status !== "verified" && (
          <span className="flex items-center gap-1 text-sm font-semibold text-error">
            <Icon name="cancel" className="text-[16px]" />
            {result.config.status === "failed"
              ? `Failed: ${result.config.last_error ?? "verification failed"}`
              : "Saved (unverified)"}
          </span>
        )}
        {result && !result.ok && (
          <span className="text-sm text-error">{result.message}</span>
        )}
      </div>
      <p className="mt-2 text-[11px] text-on-surface-variant/60">
        Saving makes one small real test request to the provider to verify the
        key/endpoint works.
      </p>
    </section>
  );
}

function ConfigRow({
  config,
  onUpdated,
  onDeleted,
}: {
  config: LLMConfig;
  onUpdated: (config: LLMConfig) => void;
  onDeleted: (id: string) => void;
}) {
  const meta = PROVIDER_META[config.provider_type as Provider];
  const [checking, setChecking] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);
  const { confirm, dialog: confirmDialog } = useConfirm();

  const recheck = async () => {
    setChecking(true);
    setRowError(null);
    try {
      const updated = await verifyLLMConfig(config.id);
      onUpdated(updated);
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : "Could not recheck this config.");
    } finally {
      setChecking(false);
    }
  };

  const remove = async () => {
    const ok = await confirm({
      title: "Delete LLM config",
      message: `Delete "${config.label || meta?.label || config.provider_type}"? This can't be undone.`,
      confirmLabel: "Delete",
      danger: true,
    });
    if (!ok) return;
    setDeleting(true);
    setRowError(null);
    try {
      await deleteLLMConfig(config.id);
      onDeleted(config.id);
    } catch (err) {
      setRowError(err instanceof ApiError ? err.message : "Could not delete this config.");
      setDeleting(false);
    }
  };

  const statusBadge =
    config.status === "verified" ? (
      <span className="flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400">
        <Icon name="check_circle" filled className="text-[14px]" />
        Verified
      </span>
    ) : config.status === "failed" ? (
      <span className="flex items-center gap-1 rounded-full bg-error/10 px-2.5 py-1 text-xs font-semibold text-error">
        <Icon name="cancel" className="text-[14px]" />
        Failed
      </span>
    ) : (
      <span className="flex items-center gap-1 rounded-full bg-warn/10 px-2.5 py-1 text-xs font-semibold text-warn">
        <Icon name="help" className="text-[14px]" />
        Unverified
      </span>
    );

  return (
    <div className="glass-card flex flex-col gap-2 rounded-xl p-4 sm:flex-row sm:items-center sm:justify-between">
      {confirmDialog}
      <div className="flex min-w-0 items-center gap-3">
        <Icon name={meta?.icon ?? "smart_toy"} className="shrink-0 text-primary" />
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 truncate text-sm font-semibold text-on-surface">
            {config.label || meta?.label || config.provider_type}
            {config.image_capable && (
              <span
                className="rounded-full bg-pink-500/10 px-1.5 py-0.5 text-[10px] font-bold text-pink-400"
                title="Can be assigned to the Image agent role"
              >
                🖼️ Image-capable
              </span>
            )}
          </p>
          <p className="truncate font-code-sm text-[11px] text-on-surface-variant">
            {config.key_preview ?? config.base_url ?? "—"} · {config.model}
          </p>
          {config.status === "failed" && config.last_error && (
            <p className="mt-0.5 truncate text-[11px] text-error">{config.last_error}</p>
          )}
          {rowError && <p className="mt-0.5 text-[11px] text-error">{rowError}</p>}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {statusBadge}
        <button
          type="button"
          onClick={recheck}
          disabled={checking || deleting}
          className="flex items-center gap-1 rounded-lg border border-outline-variant/20 bg-surface-container-high px-2.5 py-1.5 text-xs text-on-surface transition-colors hover:bg-surface-variant/30 disabled:opacity-50"
        >
          <Icon name="sync" className={`text-[14px] ${checking ? "animate-spin" : ""}`} />
          Recheck
        </button>
        <button
          type="button"
          onClick={remove}
          disabled={checking || deleting}
          className="flex items-center gap-1 rounded-lg border border-error/20 bg-error/5 px-2.5 py-1.5 text-xs text-error transition-colors hover:bg-error/10 disabled:opacity-50"
        >
          <Icon name="delete" className="text-[14px]" />
          Delete
        </button>
      </div>
    </div>
  );
}

export default function SettingsClient() {
  const { configs, setConfigs, loading: loadingConfigs, notDeployed: configsNotDeployed, error: configsError } =
    useLLMConfigs();
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [settingsLoading, setSettingsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getSettings()
      .then((data) => {
        if (!cancelled) setSettings(data);
      })
      .catch(() => {
        // non-fatal: run-limits section just stays empty
      })
      .finally(() => {
        if (!cancelled) setSettingsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />
      <main className="min-h-screen flex-1 bg-background md:ml-[280px]">
        <Topbar searchPlaceholder="Search…" />
        <div className="mx-auto max-w-4xl space-y-8 p-8">
          <div>
            <h2 className="font-headline-md text-headline-md font-bold tracking-tight text-on-surface">
              System Settings
            </h2>
            <p className="mt-1 font-body-md text-body-md text-on-surface-variant/80">
              Curator has no user accounts in this version — LLM configs
              below are shared system-wide, not personal preferences.
            </p>
          </div>

          {configsNotDeployed && (
            <div className="glass-panel flex items-start gap-3 rounded-2xl p-6 text-warn">
              <Icon name="build" className="mt-0.5 shrink-0" />
              <div>
                <p className="font-headline-sm text-headline-sm text-on-surface">
                  Backend not updated yet
                </p>
                <p className="mt-1 text-sm text-on-surface-variant">
                  <code className="rounded bg-surface-container-highest px-1.5 py-0.5 font-code-sm text-code-sm">
                    /api/llm-configs
                  </code>{" "}
                  returned 404. This endpoint is being added on the backend —
                  reload this page once it&apos;s deployed.
                </p>
              </div>
            </div>
          )}
          {configsError && (
            <div className="glass-panel flex items-start gap-3 rounded-2xl p-6 text-error">
              <Icon name="error" className="mt-0.5 shrink-0" />
              <p className="text-sm text-error/80">{configsError}</p>
            </div>
          )}

          {!configsNotDeployed && (
            <>
              <AddLLMForm onCreated={(c) => setConfigs((prev) => [c, ...prev])} />

              <section>
                <h3 className="mb-3 font-headline-sm text-headline-sm text-on-surface">
                  Saved LLM configs
                </h3>
                {loadingConfigs ? (
                  <p className="text-sm text-on-surface-variant">Loading…</p>
                ) : configs.length === 0 ? (
                  <p className="text-sm text-on-surface-variant">
                    No LLM configs saved yet. Add one above.
                  </p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {configs.map((c) => (
                      <ConfigRow
                        key={c.id}
                        config={c}
                        onUpdated={(updated) =>
                          setConfigs((prev) =>
                            prev.map((p) => (p.id === updated.id ? updated : p)),
                          )
                        }
                        onDeleted={(id) =>
                          setConfigs((prev) => prev.filter((p) => p.id !== id))
                        }
                      />
                    ))}
                  </div>
                )}
              </section>
            </>
          )}

          <OllamaSetupPanel />

          {!settingsLoading && settings && (
            <section className="glass-panel rounded-2xl p-6">
              <h3 className="mb-2 font-headline-sm text-headline-sm text-on-surface">
                Run limits
              </h3>
              <div className="flex items-center justify-between border-b border-outline-variant/10 py-3">
                <p className="text-sm text-on-surface-variant">Max supervisor turns</p>
                <p className="font-code-sm text-code-sm text-on-surface">
                  {settings.max_supervisor_turns ?? "—"}
                </p>
              </div>
              <div className="flex items-center justify-between border-b border-outline-variant/10 py-3">
                <p className="text-sm text-on-surface-variant">Max debate rounds</p>
                <p className="font-code-sm text-code-sm text-on-surface">
                  {settings.max_debate_rounds ?? "—"}
                </p>
              </div>
              <div className="flex items-center justify-between py-3">
                <p className="text-sm text-on-surface-variant">Max searches per run</p>
                <p className="font-code-sm text-code-sm text-on-surface">
                  {settings.max_searches_per_run ?? "—"}
                </p>
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  );
}

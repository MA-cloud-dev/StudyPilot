"use client";

import { useId, useState, type FormEvent } from "react";

import { QueryStateCard } from "@/components/query-state-card";
import { getErrorMessage } from "@/lib/api/errors";
import {
  useDeleteKnowledgeAsset,
  useKnowledgeAssets,
  useRetryKnowledgeAsset,
  useUploadKnowledgeAssets,
} from "@/lib/hooks/use-knowledge-assets";

export default function KnowledgePage() {
  const fileInputId = useId();
  const query = useKnowledgeAssets();
  const uploadMutation = useUploadKnowledgeAssets();
  const retryMutation = useRetryKnowledgeAsset();
  const deleteMutation = useDeleteKnowledgeAsset();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");

  const assets = query.data?.assets ?? [];

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (selectedFiles.length === 0) {
      return;
    }

    const formData = new FormData();
    for (const file of selectedFiles) {
      formData.append("files", file);
    }
    if (title.trim()) {
      formData.append("title", title.trim());
    }
    if (tags.trim()) {
      formData.append("tags", tags.trim());
    }

    await uploadMutation.mutateAsync(formData);
    setSelectedFiles([]);
    setTitle("");
    setTags("");
  };

  return (
    <div className="space-y-12">
      <header className="border-b border-slate-200 pb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.25em] text-accent">Knowledge</p>
        <h2 className="mt-4 text-3xl font-bold text-ink">知识仓库</h2>
        <p className="mt-4 max-w-3xl text-sm leading-relaxed text-slate-600">
          上传学习资料后，计划生成和学习答疑会优先利用 ready 状态的知识内容。
        </p>
      </header>

      <div className="grid gap-8 xl:grid-cols-[1fr_1.15fr]">
        <section className="border border-slate-200 bg-white p-8">
          <div className="space-y-2 border-b border-slate-100 pb-4 mb-6">
            <h3 className="text-xl font-bold text-ink">上传资料</h3>
            <p className="text-sm text-slate-500">支持一次上传多个文件，失败资料可在右侧列表直接重试。</p>
          </div>

          <form className="space-y-6" onSubmit={handleUpload}>
            <label
              className="flex min-h-48 cursor-pointer flex-col items-center justify-center border border-dashed border-slate-300 bg-slate-50 px-6 py-8 text-center transition hover:border-ink"
              htmlFor={fileInputId}
            >
              <span className="text-base font-bold text-ink">点击选择资料文件</span>
              <span className="mt-2 text-sm text-slate-500">建议上传 `.md`、`.txt`、文本型 `.pdf`。</span>
              <span className="mt-4 text-xs font-semibold uppercase tracking-[0.25em] text-accent">
                {selectedFiles.length > 0 ? `${selectedFiles.length} file(s) ready` : "waiting for files"}
              </span>
            </label>
            <input
              className="sr-only"
              id={fileInputId}
              multiple
              onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
              type="file"
            />

            <label className="block space-y-2">
              <span className="text-sm font-medium text-ink">统一标题（可选）</span>
              <input
                className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink"
                onChange={(event) => setTitle(event.target.value)}
                placeholder="例如：概率论课堂笔记"
                value={title}
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-ink">标签（逗号分隔，可选）</span>
              <input
                className="w-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-ink"
                onChange={(event) => setTags(event.target.value)}
                placeholder="例如：probability, week1, textbook"
                value={tags}
              />
            </label>

            {uploadMutation.error ? <p className="text-sm text-red-600">{getErrorMessage(uploadMutation.error)}</p> : null}

            <div className="pt-4 border-t border-slate-100">
              <button
                className="bg-accent px-6 py-3 text-sm font-bold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={selectedFiles.length === 0 || uploadMutation.isPending}
                type="submit"
              >
                {uploadMutation.isPending ? "上传中..." : "上传资料"}
              </button>
            </div>
          </form>
        </section>

        <QueryStateCard
          title="资料列表"
          action={<span className="text-sm font-medium text-slate-500">{assets.length} item(s)</span>}
          loading={query.isLoading}
          error={query.error ? getErrorMessage(query.error) : null}
          empty={assets.length === 0}
          emptyMessage="当前还没有资料，先上传一份文本资料让计划生成有可用上下文。"
        >
          <div className="space-y-4">
            {assets.map((asset) => (
              <article className="border border-slate-200 p-5 transition hover:border-ink" key={asset.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <h3 className="text-lg font-bold text-ink">{asset.title}</h3>
                    <p className="text-sm text-slate-500">
                      {asset.file_type} · {asset.status}
                    </p>
                    {asset.parse_error_reason ? (
                      <p className="text-sm text-red-600">失败原因: {asset.parse_error_reason}</p>
                    ) : null}
                    {asset.tags && asset.tags.length > 0 ? (
                      <div className="flex flex-wrap gap-2 pt-3">
                        {asset.tags.map((tag) => (
                          <span className="bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600" key={tag}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2 mt-2 sm:mt-0">
                    {asset.status === "parse_failed" ? (
                      <button
                        className="border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-ink transition hover:bg-slate-50"
                        disabled={retryMutation.isPending}
                        onClick={() => retryMutation.mutate(asset.id)}
                        type="button"
                      >
                        重试解析
                      </button>
                    ) : null}
                    <button
                      className="border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-700 transition hover:bg-red-50"
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(asset.id)}
                      type="button"
                    >
                      删除
                    </button>
                  </div>
                </div>
              </article>
            ))}
            {retryMutation.error ? <p className="text-sm text-red-600">{getErrorMessage(retryMutation.error)}</p> : null}
            {deleteMutation.error ? <p className="text-sm text-red-600">{getErrorMessage(deleteMutation.error)}</p> : null}
          </div>
        </QueryStateCard>
      </div>
    </div>
  );
}

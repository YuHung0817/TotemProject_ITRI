const BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${BASE}/health`);
  if (!response.ok) throw new Error(`服務連線失敗（錯誤代碼：${response.status}）`);
  return response.json();
}

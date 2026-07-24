import { FormEvent, useEffect, useRef, useState } from "react";
import type { AssetType, CollectionRecord, GalleryAsset, GenerateRequest, ImageRecord } from "./types";

const API = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";
const SERVER = API.replace(/\/api\/v1\/?$/, "");
const products = [
  // "棒球帽","漁夫帽","圓領T-shirt","短版T-shirt","Polo衫","帽T",
  // "拉鍊帽T","飛行外套","牛仔外套","教練外套","背心",
  "托特包","帆布袋","束口袋","午餐袋","飲料提袋","環形鑰匙圈","台灣高中生側背書包","貝殼零錢包","圖騰織帶手機掛繩",
];
const autoPlacement = "AI自動決定位置";
const placementByProduct: Record<string,string[]> = {
  // "棒球帽":[autoPlacement,"帽前","帽簷","帽子右前側邊線"],
  // "漁夫帽":[autoPlacement,"帽子右前側邊線","帽子整圈織帶"],
  // "圓領T-shirt":[autoPlacement,"左胸","胸前中央","背面中央","左袖","右袖","下擺","下擺及左右袖口反摺處","右前側肩膀到下擺"],
  // "短版T-shirt":[autoPlacement,"左胸","胸前中央","背面中央","左袖","右袖","下擺","下擺及左右袖口反摺處","右前側肩膀到下擺"],
  // "Polo衫":[autoPlacement,"左胸","胸前中央","左袖及右袖"],
  // "帽T":[autoPlacement,"胸前中央","左袖","右袖","下擺"],
  // "拉鍊帽T":[autoPlacement,"左胸","左袖","右袖","下擺","下擺及左右袖口"],
  // "飛行外套":[autoPlacement,"左袖","右袖","口袋蓋","下擺及左右袖口"],
  // "牛仔外套":[autoPlacement,"左袖","右袖","口袋蓋","下擺及左右袖口"],
  // "教練外套":[autoPlacement,"左袖","右袖","口袋蓋","下擺及左右袖口"],
  // "背心":["背心整圈邊框"],
  "托特包":[autoPlacement,"袋子中央","提袋處"],
  "帆布袋":[autoPlacement,"袋子中央","提袋處"],
  "束口袋":[autoPlacement,"袋子中央"], "午餐袋":[autoPlacement,"袋子中央","提袋"],
  "飲料提袋":["袋身／杯套本體","提把／提帶"], "環形鑰匙圈":["圖騰取代皮革帶"],
  "台灣高中生側背書包":[autoPlacement,"翻蓋偏下方","肩帶"],
  "貝殼零錢包":[autoPlacement,"袋身中央直條"],
  "圖騰織帶手機掛繩":["圖騰取代整條織帶"],
};
const elementNames = ["山豬","山羌","山羊","水鹿","台灣黑熊","月亮","太陽","山脈","河川","鳥","小米","菖蒲","葫蘆","玉米","稻米","樹豆","茅草","星星","菱形","射耳祭"];
const fallbackElementImage = "/elements/botton＿tent.png";
const elementImages: Record<string, string> = {
  山豬: "/elements/botton＿山豬.svg",
  山羌: "/elements/botton＿山羌.svg",
  山羊: "/elements/botton＿山羊.svg",
  水鹿: "/elements/botton＿水鹿.svg",
  台灣黑熊: "/elements/botton＿台灣黑熊.svg",
  月亮: "/elements/botton＿月亮.svg",
  太陽: "/elements/botton＿太陽.svg",
  山脈: "/elements/botton＿山脈.svg",
  河川: "/elements/botton＿河川.svg",
  鳥: "/elements/botton＿鳥.svg",
  小米: "/elements/botton＿小米.svg",
  菖蒲: "/elements/botton＿菖蒲.svg",
  葫蘆: "/elements/botton＿葫蘆.svg",
  玉米: "/elements/botton＿玉米.svg",
  稻米: "/elements/botton＿稻米.svg",
  樹豆: "/elements/botton＿樹豆.svg",
  茅草: "/elements/botton＿茅草.svg",
  星星: "/elements/botton＿星星.svg",
  菱形: "/elements/botton＿菱形.svg",
  射耳祭: "/elements/botton＿射耳祭.svg",
};
type RevisionExchange = { id:string; createdAt?:number; user:string; sourceImage:string; reply:string; image?:ImageRecord; pending:boolean };
type GenerationExchange = { id:string; createdAt?:number; prompt:string; elements:string[]; reply:string; images:ImageRecord[]; pending:boolean; hideUserMessage?:boolean };
type StoredChat = { id:string; title:string; revisionExchanges:RevisionExchange[]; generationExchanges:GenerationExchange[] };
type RevisionMode = "elements" | "palette" | "same" | "product";

function normalizeGenerationExchange(exchange:GenerationExchange):GenerationExchange {
  if (exchange.images.length === 0 || !exchange.pending) return exchange;
  return {...exchange,reply:`完成了！這是相同圖案的 ${exchange.images.length} 組配色。`,pending:false};
}

async function readResponse(response: Response): Promise<any> {
  if (response.status===401) window.dispatchEvent(new Event("totem:unauthorized"));
  const text = await response.text();
  if (!text) return {};
  try { return JSON.parse(text); }
  catch { return { detail: text }; }
}

const wait = (milliseconds:number) => new Promise(resolve => window.setTimeout(resolve, milliseconds));

function formatExpiry(value?:string):string {
  if (!value) return "到期時間載入中";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "到期時間未知";
  return new Intl.DateTimeFormat("zh-TW", {year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",hour12:false}).format(date);
}

async function downloadImage(url:string, filename:string):Promise<void> {
  const response=await fetch(url);
  if (!response.ok) throw new Error(`下載失敗 (${response.status})`);
  const blob=await response.blob();
  const objectUrl=URL.createObjectURL(blob);
  const link=document.createElement("a");
  link.href=objectUrl;
  link.download=filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}

function ExpiryLabel({expiresAt}:{expiresAt?:string}) {
  return <small className="expiry-label">預計於 {formatExpiry(expiresAt)} 到期</small>;
}

async function waitForGenerationJob(jobId:string):Promise<{images:ImageRecord[]}> {
  for (let attempt=0; attempt<300; attempt+=1) {
    await wait(2000);
    const response = await fetch(`${API}/generation-jobs/${encodeURIComponent(jobId)}`);
    const data = await readResponse(response);
    if (!response.ok) throw new Error(data.detail ?? `查詢生成狀態失敗 (${response.status})`);
    if (data.status === "succeeded") return {images:data.images};
    if (data.status === "failed") throw new Error(data.error_message ?? "圖片生成失敗");
  }
  throw new Error("圖片生成等待逾時，請稍後查看聊天室");
}

async function requestImageGeneration(payload:GenerateRequest, idempotencyKey:string, chatroomId:string, exchangeId:string):Promise<{images:ImageRecord[]}> {
  const headers = {"Content-Type":"application/json","Idempotency-Key":idempotencyKey,"X-Chatroom-Id":chatroomId,"X-Client-Exchange-Id":exchangeId};
  let response:Response;
  try {
    response = await fetch(`${API}/images/generate`, {
      method:"POST",
      headers,
      body:JSON.stringify(payload),
    });
  } catch {
    await wait(1000);
    response = await fetch(`${API}/images/generate`, {
      method:"POST",
      headers,
      body:JSON.stringify(payload),
    });
  }
  const data = await readResponse(response);
  if (response.status === 409 && data.detail?.code === "generation_in_progress") {
    return waitForGenerationJob(data.detail.job_id);
  }
  if (!response.ok) throw new Error(data.detail?.message ?? data.detail ?? `生成失敗 (${response.status})`);
  return data;
}

async function requestProtectedImage(url:string, options:RequestInit = {}, chatroomId?:string, exchangeId?:string):Promise<ImageRecord> {
  const idempotencyKey = crypto.randomUUID();
  const send = () => fetch(url, {
    ...options,
    headers:{
      ...(options.headers ?? {}),
      "Idempotency-Key":idempotencyKey,
      ...(chatroomId ? {"X-Chatroom-Id":chatroomId} : {}),
      ...(exchangeId ? {"X-Client-Exchange-Id":exchangeId} : {}),
    },
  });
  let response:Response;
  try {
    response = await send();
  } catch {
    await wait(1000);
    response = await send();
  }
  const data = await readResponse(response);
  if (response.status === 409 && data.detail?.code === "generation_in_progress") {
    const completed = await waitForGenerationJob(data.detail.job_id);
    if (!completed.images[0]) throw new Error("生成完成，但找不到圖片結果");
    return completed.images[0];
  }
  if (!response.ok) throw new Error(data.detail?.message ?? data.detail ?? `圖片生成失敗 (${response.status})`);
  return data;
}

async function requestChatroom(chatroomId:string):Promise<StoredChat> {
  const response = await fetch(`${API}/chatrooms/${encodeURIComponent(chatroomId)}`);
  const data = await readResponse(response);
  if (!response.ok) throw new Error(data.detail ?? `讀取聊天室失敗 (${response.status})`);
  return data;
}

const detailViews:AssetType[] = ["motif","preview","chart"];
const CloseButtonIcon = () => <svg className="close-button-icon" viewBox="0 0 45 45" aria-hidden="true"><circle cx="22.5" cy="22.5" r="22.5"/><path d="m16 16 13 13m0-13L16 29"/></svg>;
const SimilarIcon = () => <svg className="similar-icon" viewBox="0 0 36 36" aria-hidden="true"><path className="wand-body" fillRule="evenodd" d="M3.8 25.2 19.2 9.8a5.4 5.4 0 0 1 7.6 7.6L11.4 32.8a5.4 5.4 0 0 1-7.6-7.6Zm4.1 1.3L21 13.4a1.5 1.5 0 1 1 2.1 2.1L10 28.6a1.5 1.5 0 1 1-2.1-2.1Z"/><path className="wand-rays" d="M25 3v4M31.4 5.6l-2.8 2.8M33 12h-4M31.4 18.4l-2.8-2.8M18.6 5.6l2.8 2.8"/></svg>;
const MenuIcon = () => <svg className="menu-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M5 12h14M5 17h14"/></svg>;
const BackIcon = () => <svg className="back-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m15 5-7 7 7 7"/></svg>;
const BookmarkIcon = ({filled=false}:{filled?:boolean}) => <svg className="bookmark-icon" viewBox="0 0 24 24" aria-hidden="true"><path className={filled?"filled":""} d="M6.5 3.5h11v17l-5.5-3.6-5.5 3.6z"/></svg>;
const NewChatIcon = () => <svg className="new-chat-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 3.5h9l4 4v4.2M14 3.5v4h4M12.5 19.5H5V3.5"/><path d="m11.5 18.5 6.7-6.7 2 2-6.7 6.7-2.7.7z"/></svg>;
const ElementsIcon = () => <svg className="elements-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 4 6.5H8z"/><rect x="3.5" y="13" width="7" height="7" rx="1"/><circle cx="17" cy="16.5" r="3.5"/></svg>;
const MoonTagIcon = () => <svg className="moon-tag-icon" viewBox="0 0 21 20" fill="none" aria-hidden="true"><path d="M19.3695 12.6835C18.2431 12.852 17.0941 12.7474 16.0139 12.3783C14.9337 12.0091 13.9522 11.3854 13.1474 10.5569C12.3426 9.72846 11.7367 8.71803 11.3781 7.60607C11.0195 6.49411 10.9179 5.31133 11.0816 4.15186C9.2548 4.42802 7.59711 5.40521 6.44119 6.88731C5.28528 8.3694 4.71668 10.2467 4.84954 12.1424C4.98239 14.0382 5.80685 15.812 7.15746 17.108C8.50806 18.4039 10.2848 19.1261 12.1312 19.1295C13.8886 19.1296 15.5873 18.4782 16.9163 17.2944C18.2454 16.1107 19.1169 14.4739 19.3695 12.6835Z" stroke="white" strokeWidth="1.2"/><path d="M1.44385 6.68008V8.41722M2.2876 7.54865H0.600098M4.81886 0.600098V2.91628M5.94386 1.75819H3.69386" stroke="white" strokeWidth="1.2" strokeLinecap="round"/></svg>;
const BoarTagIcon = () => <svg className="element-tag-icon boar-tag-icon" viewBox="0 0 22 22" fill="none" aria-hidden="true"><path d="M21.244 4.15147 21.2206 3.86616 20.9415 3.83316C20.8968 3.828 19.8315 3.70356 18.5645 3.70356c-1.6792 0-2.8783.2176-3.5713.64694a10.8 10.8 0 0 0-.9291-.53144C13.3738 1.64106 10.8806 1.03125 10.8806 1.03125c.2757.58953.1702 1.76103.1702 1.76103-.7635-1.12784-2.3021-.78753-2.3021-.78753.70709.48297.65793 1.15603.65793 1.15603-.7865-.31075-1.85763.33035-1.85763.33035.19918.05878.39178.13791.57475.23615a12.7 12.7 0 0 0-1.18044.6655c-.7559-.484-2.12953-.72909-4.08994-.72909-.96353 0-1.69124.06187-1.72149.06462l-.280161.02441-.032313.28428C.753406 4.62378.221625 9.79481 1.89981 10.7333c.07265.0403.15194.0689.23788.0859a10.1 10.1 0 0 0-.38191 2.7386c-.00034 6.5303 4.67294 7.411 9.24442 7.411 4.5716 0 9.2449-.8807 9.2449-7.4113 0-.9426-.1334-1.88-.3967-2.7937.0609-.0167.1182-.0396.1719-.0687 1.6407-.89307 1.2711-5.96919 1.2237-6.54363ZM19.6957 10.0784c-.045.0241-.1471.023-.2481.0028l-.5872-.11864.1953.57574c.3315.9722.5011 1.9921.5022 3.0192 0 5.8981-4.113 6.7114-8.558 6.7114-4.44502 0-8.55731-.813-8.55731-6.7114 0-1.0127.16638-2.0216.49535-2.9978l.20659-.61364-.61669.16124c-.13509.0357-.2499.0381-.29734.012-.91816-.51321-.95597-3.65852-.75831-5.71414.46046-.02792.92118-.04202 1.38101-.04228 1.93909 0 3.31099.25678 3.86236.72256l.198.16706.21313-.14575a10.4 10.4 0 0 1 1.67131-.91575c1.51077 1.29284 2.19827 3.67881 2.19827 3.67881.3262-2.07694 1.5376-3.13534 2.343-3.62347.5131.2287 1.0051.50188 1.4706.81641l.209.14094.1956-.15985c.5056-.41353 1.695-.64109 3.3491-.64109.8494 0 1.6198.05947 2.0161.09625.1341 2.01713.011 5.09128-.8845 5.5794Z" fill="white"/><path d="M11 12.6976c-2.98997 0-4.92219 1.7332-4.92219 4.4158 0 2.5125 1.67309 2.7205 3.5365 2.7205.2145 0 .43549-.0028.66239-.0055.4716-.0062.9759-.0062 1.4472 0 .2268.0032.4476.005.6624.0055 1.8634 0 3.5365-.208 3.5365-2.7205-.0004-2.6826-1.9326-4.4158-4.9228-4.4158Zm-2.08076 5.9688c.63105 0 1.14266-.9588 1.14266-2.1415 0-1.1828-.51161-2.1416-1.14266-2.1416-.63106 0-1.14263.9588-1.14263 2.1416 0 1.1827.51157 2.1415 1.14263 2.1415Zm4.16216 0c.6307 0 1.1419-.9588 1.1419-2.1415 0-1.1828-.5112-2.1416-1.1419-2.1416s-1.1419.9588-1.1419 2.1416c0 1.1827.5112 2.1415 1.1419 2.1415Z" fill="white"/></svg>;
const SunTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M18.3333 10.0002h.8333M9.99992 1.66683V.833496M9.99992 19.1668v-.8333M16.6666 16.6668l-.8333-.8333M16.6666 3.3335l-.8333.83333M3.33325 16.6668l.83334-.8333M3.33325 3.3335l.83334.83333M.833252 10.0002h.833338M9.99992 15.0002a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const DeerTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M18.9125 8.84412c-.0215-.04781-.0456-.09125-.0684-.13656 1.4403-1.37594-.5062-3.69907-.5062-3.69907s-.5369 1.53532-.655 2.61c-.021-.00531-.0419-.01312-.0632-.01718-1.0084-.18532-2.1693-.27157-3.6534-.27157-.6838 0-1.34.0175-1.9747.03407-.5481.01437-1.0659.02812-1.5309.02812-1.67066 0-1.9291-.21344-1.96847-.27844.00094-.815-.16031-1.58531-.46813-2.2525.53282-.76218.53907-1.83000.36532-2.28531-.14469-.37969-.41782-.42094-.52875-.42094-.07729 0-.15136.01761-.22219.05282-.10406.05125-.27156.135-.46625.24187.75656-.60937 1.76719-.66031 1.76719-.66031-1.75188-.64813-2.73469.09687-3.22844.91531.42219-1.44937 2.07031-2.07656 2.07031-2.07656-2.26906-.07875-3.07531 1.24312-3.29594 2.37062-.395.14063-.775.37844-1.12468.71188-.745.71156-.88688 1.25531-1.03719 1.83031-.1575.60313-.35344 1.35375-1.42125 2.73469-.35625.46125-.29281.86531-.22281 1.06531.1675.48094.68625.82344 1.49844.99032.01343.0028.02937.005.04375.0075-.04594 1.2187 1.55249 1.7731 1.55249 1.7731s-.52531-.9281-.14312-2.20373c.16094-.08813.37563-.11938.60344-.15219.24813-.03594.55125-.08.83375-.22594.15125 1.30376.59625 3.27346 1.88281 4.86536.05907.2996.23157 1.595-.4375 4.3896l-.14187.5929h1.90812l.11-.3132.92938-2.649.03625-.1025-.01063-.1088c-.03781-.4006-.03218-.849.00782-1.0987.39031.1084.86906.1615 1.45406.1615 1.6709 0 3.71-.4428 4.499-.6306.4072.6047 1.0825 1.1281 1.4816 1.4072-.13.4953-.3156 1.4603-.29 2.8656l.0088.4685h1.9078l.0559-.4104c.1025-.754.6247-3.4237.63-3.4506l.0266-.1353-.0469-.1291c-.3238-.8931-.3225-1.3684-.3122-1.5081.8631-1.6772.6825-3.7056.1409-4.89748Z" fill="white"/><circle cx="4.05" cy="6.07" r=".47" fill="#6E93CC"/></svg>;
const MountainTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="M14.0666 17.3333H2.3999L5.0874 9.63C6.39573 5.87667 7.0499 4 8.23323 4c1.11417 0 1.76 1.66667 2.92667 5" stroke="white" strokeLinecap="round" strokeLinejoin="round"/><path d="M5.73315 17.3332H19.0665l-3.8275-6.1175c-1.2725-2.03336-1.9083-3.0492-2.8392-3.0492-.9316 0-1.5666 1.01667-2.83915 3.0492l-1.22083 1.9508" stroke="white" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const RiverTagIcon = () => <svg className="element-tag-icon river-tag-icon" viewBox="0 0 18 18" fill="none" aria-hidden="true"><path d="M4.42 2.22c.92 0 1.82.3 2.61.89a7.7 7.7 0 0 0-.79 1.97l-5.11.56V3.56c1.06-.92 2.21-1.34 3.29-1.34Zm8.16-.72c1.21 0 2.42.59 3.59 1.54.24.19.47.4.7.61v1.84l-8.95-.38c.58-2 2.56-3.47 4.41-3.6l.25-.01ZM6.84 6.91c-.3.7-.04.92 1.11 1.32 1.3.45 3.65.46 2.8.68-1.57.78-4.55 1.13-4.6 1.74-.05.62 5.4.91 6.39 1.89-.84.42-1.5 1.2-2.02 1.53.55.02 1.02-.13 1.47-.38 2.12-1.17 2.04-.17.58.74-.71.45-1.5.8-1.24 1.61.33.54 1.18.88 1.48 1.11h-.64c-.59-.31-1.15-.67-1.65-1.03-.39.44-.12.83.01 1.03h-1.24c-.46-.38-1-.86-.93-1.14.07-.31.73-.86 1.49-1.34-.65.15-2.08.59-2.64 1.21-.35.39-.09.93.08 1.27h-.39c-.4-.45-.76-.93-1.08-1.4-.7.39-.34 1.12-.18 1.4h-.63c-.16-1.79.91-2.42 3.46-3.15.72-.21-1.42-.99-2.39-1.35l.12-.81c-1.3-.49-3.32-1.4-4.77-1.25 1.11-.65 2.71-.66 5.85-1.13-1.12-.53-3.38-1.06-2.86-1.47.37-.29 1.56-.56 2.94-.77Z" stroke="white" strokeLinejoin="round"/></svg>;
const WaterDeerTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7.2 8.1c-2.4-2.8-4.8-2.2-5.6-.7-.7 1.4.2 4.2 4.1 4.4M16.8 8.1c2.4-2.8 4.8-2.2 5.6-.7.7 1.4-.2 4.2-4.1 4.4M7.2 7.9C7.2 4.6 9.3 3 12 3s4.8 1.6 4.8 4.9v5.2c0 4.5-2.1 8.4-4.8 8.4s-4.8-3.9-4.8-8.4V7.9ZM8.8 4.4C7.2 3.2 6.7 1.9 6.7.6M15.2 4.4c1.6-1.2 2.1-2.5 2.1-3.8M10.1 4C9 2.8 8.8 1.8 8.9.8M13.9 4c1.1-1.2 1.3-2.2 1.2-3.2" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><circle cx="10" cy="11" r=".75" fill="white"/><circle cx="14" cy="11" r=".75" fill="white"/><circle cx="12" cy="15.2" r=".9" fill="white"/></svg>;
const GoatTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M2.2 2.5C8.7.8 16.8 5.3 21.5 13.8l-1.7 5.1c-5.4-.2-10.5-1.3-13.2-4.1M2.2 2.5l6 2.9-5.9 7M6.6 14.8c-.9 2-1.5 4.1-1.7 6.3" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const BearTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3.7 9.1A5.1 5.1 0 1 1 9 2.7c1.9-.4 4.1-.4 6 0a5.1 5.1 0 1 1 5.3 6.4 9.8 9.8 0 0 1 1.2 4.7c0 5.2-4.3 8.7-9.5 8.7s-9.5-3.5-9.5-8.7c0-1.7.4-3.3 1.2-4.7Z" stroke="white" strokeWidth="1.4" strokeLinejoin="round"/><path d="m7.1 5.3.8.8m8.2 0 .8-.8M9.8 10.3v1.2m4.4-1.2v1.2M9.8 16.1h4.4M12 16.1v2.1" stroke="white" strokeWidth="1.4" strokeLinecap="round"/></svg>;
const BirdTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M1.5 9.5C5.8 2.7 9.2 3.1 13 7.4c2.2 2.5 4.2 2.3 9.5-.5-.7 3.6-2 6.4-3.8 8.8l3.3-.8c-4.1 4.2-8.3 6.2-12.5 5.6-3.8-.5-6.4-4.2-8-11Z" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><circle cx="7" cy="9.7" r="1" fill="white"/></svg>;
const MilletTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 22c1-8.8 2.4-14.8 9.4-19M6 22c2.4-6.5 5.6-10.1 11.8-12.1M4.2 22C2.8 16.2 3 11.5 1.5 9.4M6 22c3.9-5.1 7.3-5.5 11.4-.9" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><g fill="white"><ellipse cx="10.2" cy="5.4" rx="1" ry="1.7" transform="rotate(-28 10.2 5.4)"/><ellipse cx="12.9" cy="3.5" rx="1" ry="1.7" transform="rotate(20 12.9 3.5)"/><ellipse cx="15.8" cy="2.5" rx="1" ry="1.7" transform="rotate(45 15.8 2.5)"/><ellipse cx="17.3" cy="7.7" rx="1.7" ry="1" transform="rotate(12 17.3 7.7)"/><ellipse cx="19.9" cy="9.4" rx="1.7" ry="1" transform="rotate(28 19.9 9.4)"/><ellipse cx="13.4" cy="10.8" rx="1" ry="1.7" transform="rotate(40 13.4 10.8)"/><ellipse cx="16.2" cy="10.2" rx="1" ry="1.7" transform="rotate(55 16.2 10.2)"/><ellipse cx="19.2" cy="10.8" rx="1.7" ry="1" transform="rotate(15 19.2 10.8)"/></g></svg>;
const CalamusTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7.2 21.8V8.4C7.2 5 8.7 2.2 10.8.8c2.2 1.5 3.8 4.6 3.8 8.4v4.2M2.5 15.2h5c3.2 0 5.8 2.7 5.8 6v.6H7.7c-3.1 0-5.2-2.5-5.2-5.6v-1ZM13.3 21.8v-.7c0-4.8 3.4-8.4 8.2-8.4v2.8c0 3.5-2.8 6.3-6.3 6.3h-1.9Z" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><path d="M8.2 5.7h2.6L9.4 9h2.7l-1.5 3.4h2.8" stroke="white" strokeWidth="1.4" strokeLinejoin="miter"/></svg>;
const GourdTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M4 4.2c3.4-1.8 6.2-.6 7.3 1.5M8.2 4.7c1.3-1.6 4.5-1.7 6.2.4 1.1 1.3 1.1 3 2.4 4.1 2.7 2.1 4.2 4.2 4.2 7 0 4-3.5 6.8-8.1 6.8-4.8 0-8.4-3.3-8.4-7.7 0-2.7 1.2-4.7 1.1-6.5-.1-1.8-.4-3.1 2.6-4.1Z" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const CornTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 21c4.3-4.4 5.6-8 5.3-12.6 2.5 1.8 3.3 3.5 3.2 5.5M10.3 9.6C14.8 5.8 18.5 3 21.5 2.2c.8 3.5-1.4 8.5-5.3 13.3M7 21.3c3.2 1.7 7.2.6 10.4-2.7 1.6-1.7 3.1-2.8 3.3-3.5-3.4-2.4-7.9-1.5-10.8 1.3L7 19.1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const ThatchTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><ellipse cx="6.4" cy="12" rx="4.3" ry="9.3" stroke="white" strokeWidth="1.4"/><ellipse cx="6.4" cy="12" rx="2.3" ry="6.2" stroke="white" strokeWidth="1.4"/><path d="M6.4 8.4v7.2M6.4 2.7h10.7c2.7 0 4.9 4.2 4.9 9.3s-2.2 9.3-4.9 9.3H6.4M10.1 3.1c2.3 2.2 3.5 5.2 3.5 8.9s-1.2 6.7-3.5 8.9M14.1 3.1c2.3 2.2 3.5 5.2 3.5 8.9s-1.2 6.7-3.5 8.9M18 3.4c2 2.1 3 4.9 3 8.6s-1 6.5-3 8.6" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const StarTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 1.8 3.1 6.3 7 1-5.1 4.9 1.2 7-6.2-3.3L5.8 21 7 14 1.9 9.1l7-1L12 1.8Z" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const DiamondTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4.2" y="4.2" width="15.6" height="15.6" rx="2.5" transform="rotate(45 12 12)" stroke="white" strokeWidth="1.5"/></svg>;
const EarFestivalTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3.2 10.2C3.2 5 7.1 1.8 12 1.8c5.1 0 8.8 3.6 8.8 8.4 0 3.7-1.9 5.3-4 7.4-1.7 1.7-2 4.6-5.7 4.6-1.9 0-3.4-.7-4.5-1.8M8 10.2c0-2.5 1.7-4.2 4-4.2 2.4 0 4.1 1.8 4.1 4.1 0 1.9-.8 2.8-2.1 4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>;
const RiceTagIcon = () => <svg className="element-tag-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M16.2 5.4c2.1.8 3.3 2.7 3.1 5.2l-.5 6.2M18.8 16.8c1.1-2.3 2.3-3.8 3.7-4.7-2.5 3.3-3.8 6.7-4 10.1-.3-3.1-1.4-5.4-3.4-7 2.1.6 3.3 1.7 3.7 3.3" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/><g stroke="white" strokeWidth="1.2"><ellipse cx="4.2" cy="13.5" rx="1.2" ry="2" transform="rotate(25 4.2 13.5)"/><ellipse cx="6.6" cy="10.6" rx="1.2" ry="2" transform="rotate(20 6.6 10.6)"/><ellipse cx="9.4" cy="8.2" rx="1.2" ry="2" transform="rotate(8 9.4 8.2)"/><ellipse cx="12.4" cy="6.3" rx="1.2" ry="2" transform="rotate(-8 12.4 6.3)"/><ellipse cx="5.5" cy="7.2" rx="2" ry="1.2" transform="rotate(12 5.5 7.2)"/><ellipse cx="8.2" cy="4.6" rx="2" ry="1.2" transform="rotate(24 8.2 4.6)"/><ellipse cx="11.5" cy="2.9" rx="2" ry="1.2" transform="rotate(35 11.5 2.9)"/></g></svg>;
function ElementTagIcon({name}:{name:string}) {
  if (name === "月亮") return <MoonTagIcon/>;
  if (name === "山豬") return <BoarTagIcon/>;
  if (name === "太陽") return <SunTagIcon/>;
  if (name === "山羌") return <DeerTagIcon/>;
  if (name === "水鹿") return <WaterDeerTagIcon/>;
  if (name === "山羊") return <GoatTagIcon/>;
  if (name === "台灣黑熊") return <BearTagIcon/>;
  if (name === "鳥") return <BirdTagIcon/>;
  if (name === "小米") return <MilletTagIcon/>;
  if (name === "菖蒲") return <CalamusTagIcon/>;
  if (name === "葫蘆") return <GourdTagIcon/>;
  if (name === "玉米") return <CornTagIcon/>;
  if (name === "茅草") return <ThatchTagIcon/>;
  if (name === "星星") return <StarTagIcon/>;
  if (name === "菱形") return <DiamondTagIcon/>;
  if (name === "射耳祭") return <EarFestivalTagIcon/>;
  if (name === "稻米") return <RiceTagIcon/>;
  if (name === "山脈") return <MountainTagIcon/>;
  if (name === "河川") return <RiverTagIcon/>;
  return null;
}
const ImagesIcon = () => <svg className="images-icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="4"/><rect x="15" y="6" width="3" height="3"/><path d="m5.5 17 4.2-5 3.2 3.3 2-2.1 3.6 4.2"/><circle cx="18" cy="18" r="3"/></svg>;
const CollectionCover = ({urls}:{urls:string[]}) => <span className="collection-cover" aria-hidden="true">{[0,1,2].map(index => <span className={`collection-cover-slot slot-${index+1}`} key={index}>{urls[index] && <img src={`${SERVER}${urls[index]}`} alt=""/>}</span>)}</span>;

function CollectionPickerPanel({collections,selectedIds,search,onSearch,onToggle,onClose,newName,onNewName,onCreate}:{collections:CollectionRecord[];selectedIds:string[];search:string;onSearch:(value:string)=>void;onToggle:(ids:string[])=>void|Promise<void>;onClose:()=>void;newName:string;onNewName:(value:string)=>void;onCreate:()=>void|Promise<void>}) {
  const nameInputRef=useRef<HTMLInputElement>(null);
  const [creating,setCreating]=useState(false);
  const visibleCollections=collections.filter(collection=>collection.name.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  async function submitNewCollection(event:React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!newName.trim()) {
      nameInputRef.current?.focus();
      return;
    }
    if (creating) return;
    setCreating(true);
    try { await onCreate(); }
    finally { setCreating(false); }
  }
  return <div className="collection-picker-backdrop" onClick={onClose}><section className="collection-picker" onClick={event=>event.stopPropagation()}><header><strong>儲存</strong></header><label className="collection-search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></svg><input value={search} onChange={event=>onSearch(event.target.value)} placeholder="搜尋"/></label><div className="collection-picker-list">{visibleCollections.map(collection=>{const selected=selectedIds.includes(collection.id);const preview=collection.preview_urls?.[0]??collection.preview_url;return <label key={collection.id}>{preview?<img className="collection-picker-thumb" src={`${SERVER}${preview}`} alt=""/>:<span className="collection-picker-thumb empty"><BookmarkIcon/></span>}<strong>{collection.name}</strong><input type="checkbox" checked={selected} onChange={()=>onToggle(selected?selectedIds.filter(id=>id!==collection.id):[...selectedIds,collection.id])}/></label>;})}</div><form className="collection-create" onSubmit={submitNewCollection}><button type="submit" disabled={creating} aria-label={newName.trim()?"建立圖版":"輸入圖版名稱"}>{creating?"…":"＋"}</button><input ref={nameInputRef} value={newName} onChange={event=>onNewName(event.target.value)} placeholder="輸入新圖版名稱" aria-label="新圖版名稱" disabled={creating}/></form></section></div>;
}

function ImageLightbox({image,view,onView,onClose}:{image:ImageRecord;view:AssetType;onView:(view:AssetType)=>void;onClose:()=>void}) {
  const [scale,setScaleState] = useState(1);
  const [offset,setOffset] = useState({x:0,y:0});
  const scaleRef = useRef(1);
  const pointers = useRef(new Map<number,{x:number;y:number}>());
  const pinch = useRef<{distance:number;scale:number}|null>(null);
  const drag = useRef<{x:number;y:number}|null>(null);
  const swipeStart = useRef<{x:number;y:number}|null>(null);
  const motifUrl=image.totem_url ?? image.url;
  const previewUrl=image.assets?.preview?.url;
  const url=view === "motif" ? `${SERVER}${motifUrl}` : view === "preview" ? (previewUrl ? `${SERVER}${previewUrl}` : null) : `${API}/images/${image.id}/cross-stitch-chart?width=100&height=50&colors=5`;

  function setScale(value:number) {
    const next=Math.min(5,Math.max(1,value)); scaleRef.current=next; setScaleState(next);
    if (next === 1) setOffset({x:0,y:0});
  }
  function reset() { pointers.current.clear();pinch.current=null;drag.current=null;setOffset({x:0,y:0});setScale(1); }
  function changeView(direction:number) {
    const index=detailViews.indexOf(view);
    const next=detailViews[(index+direction+detailViews.length)%detailViews.length];
    reset(); onView(next);
  }
  async function downloadCurrentImage() {
    if (!url) return;
    await downloadImage(url,`${image.id}-${view}.png`);
  }
  function pointerDown(event:React.PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    pointers.current.set(event.pointerId,{x:event.clientX,y:event.clientY});
    drag.current={x:event.clientX,y:event.clientY};
    if (pointers.current.size === 1) swipeStart.current={x:event.clientX,y:event.clientY};
    const points=[...pointers.current.values()];
    if (points.length === 2) pinch.current={distance:Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y),scale:scaleRef.current};
  }
  function pointerMove(event:React.PointerEvent<HTMLDivElement>) {
    if (!pointers.current.has(event.pointerId)) return;
    pointers.current.set(event.pointerId,{x:event.clientX,y:event.clientY});
    const points=[...pointers.current.values()];
    if (points.length >= 2 && pinch.current) {
      const distance=Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y);
      setScale(pinch.current.scale*distance/Math.max(1,pinch.current.distance)); return;
    }
    if (points.length === 1 && scaleRef.current > 1 && drag.current) {
      setOffset(current => ({x:current.x+event.clientX-drag.current!.x,y:current.y+event.clientY-drag.current!.y}));
      drag.current={x:event.clientX,y:event.clientY};
    }
  }
  function pointerUp(event:React.PointerEvent<HTMLDivElement>) {
    const start=swipeStart.current;
    if (pointers.current.size === 1 && scaleRef.current === 1 && start) {
      const dx=event.clientX-start.x,dy=event.clientY-start.y;
      if (Math.abs(dx)>55 && Math.abs(dx)>Math.abs(dy)*1.25) changeView(dx<0?1:-1);
      else if (dy>100 && Math.abs(dy)>Math.abs(dx)*1.25) onClose();
    }
    pointers.current.delete(event.pointerId);pinch.current=null;swipeStart.current=null;
    drag.current=[...pointers.current.values()][0] ?? null;
  }
  return <div className="detail-lightbox" role="dialog" aria-modal="true" aria-label="全螢幕圖片檢視器" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={pointerUp} onWheel={event=>{event.preventDefault();setScale(scaleRef.current*(event.deltaY<0?1.15:.87));}}>
    <header onPointerDown={event=>event.stopPropagation()}><button type="button" onClick={onClose} aria-label="關閉圖片檢視器">×</button><strong>{detailViews.indexOf(view)+1} / 3</strong><button type="button" onClick={downloadCurrentImage} disabled={!url} aria-label="另存目前圖片"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v11m0 0 4-4m-4 4-4-4M5 16v4h14v-4"/></svg></button></header>
    <div className="detail-lightbox-stage" onDoubleClick={()=>setScale(scaleRef.current>1?1:2.5)}>{url ? <img src={url} alt={assetLabels[view]} draggable={false} style={{transform:`translate(${offset.x}px,${offset.y}px) scale(${scale})`}}/> : <div className="lightbox-unavailable">商品預覽生成中…</div>}</div>
    <nav onPointerDown={event=>event.stopPropagation()}>{detailViews.map(type=><button type="button" className={type===view?"active":""} onClick={()=>{reset();onView(type);}} key={type}>{assetLabels[type]}</button>)}</nav>
  </div>;
}

function ImageCard({ image, updateImage, setStatus, askRegenerate }: { image: ImageRecord; updateImage: (oldId:string, value:ImageRecord) => void; setStatus: (value: string) => void; askRegenerate:(image:ImageRecord)=>void }) {
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailView, setDetailView] = useState<AssetType>("motif");
  const [collectionOpen, setCollectionOpen] = useState(false);
  const [collections, setCollections] = useState<CollectionRecord[]>([]);
  const [collectionSearch, setCollectionSearch] = useState("");
  const [newCollectionName, setNewCollectionName] = useState("");
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const previewAsset = image.assets?.preview;
  const previewUrl = previewAsset?.url;
  const previewRequest = previewAsset?.parameters;
  const previewRequestStarted = useRef(Boolean(previewUrl));
  const motifUrl = image.totem_url ?? image.url;
  const chartUrl = `${API}/images/${image.id}/cross-stitch-chart?width=100&height=50&colors=5`;
  const activeAsset = image.assets?.[detailView];

  function openDetail() {
    setDetailView("motif");
    setDetailOpen(true);
    if (previewUrl || previewRequestStarted.current) return;
    previewRequestStarted.current = true;
    void (async () => {
      try {
        const data = await requestProtectedImage(`${API}/images/${image.id}/preview/random`, {method:"POST"});
        updateImage(image.id, data);
      } catch (error) {
        previewRequestStarted.current = false;
        setStatus(error instanceof Error ? error.message : "商品預覽生成失敗");
      }
    })();
  }

  async function openChart() {
    const response = await fetch(`${API}/images/${image.id}/assets/chart`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        saved: true,
        parameters: { width: 100, height: 50, colors: 5 },
      }),
    });
    const data = await readResponse(response);
    if (response.ok) updateImage(image.id, data);
    setDetailView("chart");
  }

  function selectDetailView(view:AssetType) {
    if (view === "chart") void openChart();
    else setDetailView(view);
  }

  async function openCollectionPicker() {
    const response = await fetch(`${API}/images/collections`);
    const data = await readResponse(response);
    if (response.ok) setCollections(data);
    setCollectionOpen(true);
  }

  async function setAssetCollections(collectionIds:string[]) {
    const response = await fetch(`${API}/images/${image.id}/assets/${detailView}/collections`, {
      method:"PATCH", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({collection_ids:collectionIds}),
    });
    const data = await readResponse(response);
    if (response.ok) updateImage(image.id, data);
  }

  async function createAndSelectCollection() {
    const name = newCollectionName.trim();
    if (!name) return;
    const response = await fetch(`${API}/images/collections`, {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name}),
    });
    const created = await readResponse(response);
    if (!response.ok) return;
    setCollections(current => [...current, created]);
    setNewCollectionName("");
    await setAssetCollections([...(activeAsset?.collection_ids ?? []), created.id]);
  }

  return <article className="card image-card">
    <button type="button" className="image-stage image-open-button" onClick={openDetail}>
      <img src={`${SERVER}${motifUrl}`} alt={`圖騰 ${image.id}`} />
    </button>
    <button type="button" className="chat-image-regenerate" onClick={() => askRegenerate(image)} aria-label="產生類似圖騰"><SimilarIcon/><span>類似</span></button>
    {detailOpen && <div className="image-detail-page" role="dialog" aria-modal="true" aria-label="圖騰圖片詳情">
      <header className="image-detail-header"><button type="button" className="close-image-button" onClick={() => setDetailOpen(false)} aria-label="關閉圖騰詳情頁"><CloseButtonIcon /></button><strong>{assetLabels[detailView]}</strong><button type="button" disabled={!activeAsset} className={(activeAsset?.collection_ids?.length ?? 0)>0?"active":""} onClick={openCollectionPicker} aria-label="收藏目前圖片"><BookmarkIcon filled={(activeAsset?.collection_ids?.length ?? 0)>0}/></button></header>
      <div className={`image-detail-content ${detailView}`}>
        <div className="image-detail-media" onClick={() => {if (detailView !== "preview" || previewUrl) setLightboxOpen(true);}}>{detailView === "chart"
            ? <img src={`${chartUrl}&t=${Date.now()}`} alt="十字繡輔助圖"/>
            : detailView === "preview" && !previewUrl
              ? <div className="empty-preview"><span>商品預覽生成中…</span><small>完成後即可直接查看</small></div>
              : <img src={`${SERVER}${detailView === "preview" ? previewUrl : motifUrl}`} alt={assetLabels[detailView]}/>
          }</div>
        <ExpiryLabel expiresAt={image.expires_at}/>
      </div>
      <nav className="image-detail-gallery">
        <button type="button" className={detailView==="motif"?"active":""} onClick={()=>selectDetailView("motif")}><img src={`${SERVER}${motifUrl}`} alt=""/><span>圖騰原圖</span></button>
        <button type="button" className={detailView==="preview"?"active":""} onClick={()=>selectDetailView("preview")}>{previewUrl?<img src={`${SERVER}${previewUrl}`} alt=""/>:<i>生成中</i>}<span>商品展示</span></button>
        <button type="button" className={detailView==="chart"?"active":""} onClick={()=>selectDetailView("chart")}><img src={chartUrl} alt=""/><span>輔助圖</span></button>
      </nav>
      {lightboxOpen&&<ImageLightbox image={image} view={detailView} onView={selectDetailView} onClose={()=>setLightboxOpen(false)}/>} 
      {collectionOpen && <CollectionPickerPanel collections={collections} selectedIds={activeAsset?.collection_ids??[]} search={collectionSearch} onSearch={setCollectionSearch} onToggle={setAssetCollections} onClose={()=>setCollectionOpen(false)} newName={newCollectionName} onNewName={setNewCollectionName} onCreate={createAndSelectCollection}/>}
    </div>}
  </article>;
}

const assetLabels: Record<AssetType, string> = { motif: "圖騰", preview: "商品照", chart: "輔助圖" };

function GalleryAssetCard({ asset, onChanged }: {
  asset: GalleryAsset;
  onChanged: (recordId:string, assetType:AssetType, changes:Partial<Pick<GalleryAsset,"saved"|"favorite"|"collection_ids">>) => void;
}) {
  const [viewerOpen, setViewerOpen] = useState(false);
  const [collectionOpen, setCollectionOpen] = useState(false);
  const [collections, setCollections] = useState<CollectionRecord[]>([]);
  const [selectedCollectionIds, setSelectedCollectionIds] = useState<string[]>(asset.collection_ids ?? []);
  const [collectionSearch, setCollectionSearch] = useState("");
  const [newCollectionName, setNewCollectionName] = useState("");
  const [viewerScale, setViewerScale] = useState(1);
  const [viewerOffset, setViewerOffset] = useState({x:0,y:0});
  const scaleRef = useRef(1);
  const pointersRef = useRef(new Map<number,{x:number;y:number}>());
  const pinchRef = useRef<{distance:number;scale:number}|null>(null);
  const dragRef = useRef<{x:number;y:number}|null>(null);

  function setScale(value:number) {
    const next = Math.min(5,Math.max(1,value));
    scaleRef.current = next;
    setViewerScale(next);
    if (next === 1) setViewerOffset({x:0,y:0});
  }

  function resetViewer() {
    pointersRef.current.clear(); pinchRef.current = null; dragRef.current = null;
    setViewerOffset({x:0,y:0}); setScale(1);
  }

  function closeViewer() { resetViewer(); setViewerOpen(false); }

  async function downloadAsset() {
    await downloadImage(`${SERVER}${asset.url}`, `${asset.record_id}-${asset.asset_type}.png`);
  }

  function pointerDown(event:React.PointerEvent<HTMLDivElement>) {
    event.currentTarget.setPointerCapture(event.pointerId);
    pointersRef.current.set(event.pointerId,{x:event.clientX,y:event.clientY});
    dragRef.current = {x:event.clientX,y:event.clientY};
    const points = [...pointersRef.current.values()];
    if (points.length === 2) pinchRef.current = {distance:Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y),scale:scaleRef.current};
  }

  function pointerMove(event:React.PointerEvent<HTMLDivElement>) {
    if (!pointersRef.current.has(event.pointerId)) return;
    pointersRef.current.set(event.pointerId,{x:event.clientX,y:event.clientY});
    const points = [...pointersRef.current.values()];
    if (points.length >= 2 && pinchRef.current) {
      const distance = Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y);
      setScale(pinchRef.current.scale * distance / Math.max(1,pinchRef.current.distance));
      return;
    }
    if (points.length === 1 && scaleRef.current > 1 && dragRef.current) {
      const dx=event.clientX-dragRef.current.x, dy=event.clientY-dragRef.current.y;
      setViewerOffset(current => ({x:current.x+dx,y:current.y+dy}));
      dragRef.current={x:event.clientX,y:event.clientY};
    }
  }

  function pointerUp(event:React.PointerEvent<HTMLDivElement>) {
    pointersRef.current.delete(event.pointerId); pinchRef.current=null;
    const point=[...pointersRef.current.values()][0]; dragRef.current=point ?? null;
  }

  async function openCollectionPicker() {
    const response=await fetch(`${API}/images/collections`);
    const data:CollectionRecord[]=await readResponse(response);
    if (!response.ok) return;
    setCollections(data);
    if (asset.collection_ids !== undefined) setSelectedCollectionIds(asset.collection_ids);
    else {
      const membership=await Promise.all(data.map(async collection => {
        const assetsResponse=await fetch(`${API}/images/collections/${collection.id}/assets`);
        if (!assetsResponse.ok) return false;
        const assets:GalleryAsset[]=await readResponse(assetsResponse);
        return assets.some(item=>item.record_id===asset.record_id&&item.asset_type===asset.asset_type);
      }));
      setSelectedCollectionIds(data.filter((_,index)=>membership[index]).map(collection=>collection.id));
    }
    setCollectionOpen(true);
  }

  async function setAssetCollections(collectionIds:string[]) {
    const response=await fetch(`${API}/images/${asset.record_id}/assets/${asset.asset_type}/collections`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({collection_ids:collectionIds})});
    const record:ImageRecord=await readResponse(response);
    if (!response.ok) return;
    const updated=record.assets?.[asset.asset_type];
    if (updated) {
      const nextIds=updated.collection_ids??collectionIds;
      setSelectedCollectionIds(nextIds);
      onChanged(asset.record_id,asset.asset_type,{saved:updated.saved,favorite:updated.favorite,collection_ids:nextIds});
    }
  }

  async function createAndSelectCollection() {
    const name=newCollectionName.trim();
    if (!name) return;
    const response=await fetch(`${API}/images/collections`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
    const created:CollectionRecord=await readResponse(response);
    if (!response.ok) return;
    setCollections(current=>[...current,created]);
    setNewCollectionName("");
    await setAssetCollections([...selectedCollectionIds,created.id]);
  }
  return <article className="favorite-card">
    <div className="favorite-image" style={asset.width && asset.height ? {aspectRatio:`${asset.width} / ${asset.height}`} : undefined} onClick={() => setViewerOpen(true)}>
      <img src={`${SERVER}${asset.url}`} width={asset.width} height={asset.height} alt={assetLabels[asset.asset_type]}/>
      <div className="favorite-actions" onClick={event => event.stopPropagation()}>
        <button type="button" className={selectedCollectionIds.length > 0 || asset.favorite ? "active" : ""} onClick={openCollectionPicker} aria-label="收藏這張圖片"><BookmarkIcon filled={selectedCollectionIds.length > 0 || asset.favorite}/></button>
      </div>
    </div>
    <ExpiryLabel expiresAt={asset.expires_at}/>
    {viewerOpen && <div className="asset-viewer" role="dialog" aria-modal="true" aria-label="全螢幕圖片" onPointerDown={pointerDown} onPointerMove={pointerMove} onPointerUp={pointerUp} onPointerCancel={pointerUp} onWheel={event => {event.preventDefault();setScale(scaleRef.current*(event.deltaY<0?1.15:.87));}}>
      <div className="asset-viewer-toolbar" onPointerDown={event => event.stopPropagation()}><button type="button" className="close-image-button" onClick={closeViewer} aria-label="關閉圖片檢視器"><CloseButtonIcon /></button><div><button type="button" className="asset-download-button" onClick={downloadAsset} aria-label="下載目前圖片"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v11m0 0 4-4m-4 4-4-4M5 16v4h14v-4"/></svg></button></div></div>
      <img src={`${SERVER}${asset.url}`} alt={assetLabels[asset.asset_type]} draggable={false} style={{transform:`translate(${viewerOffset.x}px,${viewerOffset.y}px) scale(${viewerScale})`}}/>
    </div>}
    {collectionOpen && <CollectionPickerPanel collections={collections} selectedIds={selectedCollectionIds} search={collectionSearch} onSearch={setCollectionSearch} onToggle={setAssetCollections} onClose={()=>setCollectionOpen(false)} newName={newCollectionName} onNewName={setNewCollectionName} onCreate={createAndSelectCollection}/>}
  </article>;
}

export function ImageGeneratorPage({onLogout}:{onLogout:()=>void|Promise<void>}) {
  const [selected, setSelected] = useState<string[]>(["月亮", "山脈"]);
  const [prompt, setPrompt] = useState("");
  const [showElements, setShowElements] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("每次生成一個圖騰，再輸出圖案相同的 4 組配色。");
  const [conversationStarted, setConversationStarted] = useState(false);
  const [revisionTarget, setRevisionTarget] = useState<ImageRecord | null>(null);
  const [revisionMode, setRevisionMode] = useState<RevisionMode>("same");
  const [revisionProduct, setRevisionProduct] = useState("托特包");
  const [revisionPlacement, setRevisionPlacement] = useState(autoPlacement);
  const [revisionDisplayStyle, setRevisionDisplayStyle] = useState("白色商品＋白底");
  const [revisionExchanges, setRevisionExchanges] = useState<RevisionExchange[]>([]);
  const [generationExchanges, setGenerationExchanges] = useState<GenerationExchange[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [topbarScrolled, setTopbarScrolled] = useState(false);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [chatHistory, setChatHistory] = useState<StoredChat[]>([]);
  const [page, setPage] = useState<"chat" | "favorites" | "images">("chat");
  const [favoriteImages, setFavoriteImages] = useState<GalleryAsset[]>([]);
  const [allImages, setAllImages] = useState<GalleryAsset[]>([]);
  const [collectionFolders, setCollectionFolders] = useState<CollectionRecord[]>([]);
  const [activeCollection, setActiveCollection] = useState<CollectionRecord | null>(null);
  const [folderName, setFolderName] = useState("");
  const promptInput = useRef<HTMLInputElement>(null);
  const pageSwitchStartX = useRef<number | null>(null);
  const pageSwitchDidSwipe = useRef(false);
  const elementSheetStartY = useRef<number | null>(null);
  const [elementSheetDrag, setElementSheetDrag] = useState(0);
  const chatSaveQueue = useRef<Promise<void>>(Promise.resolve());

  function queueChatSave(chat:StoredChat) {
    chatSaveQueue.current = chatSaveQueue.current
      .catch(() => undefined)
      .then(async () => {
        const response = await fetch(`${API}/chatrooms/${encodeURIComponent(chat.id)}`, {
          method:"PUT",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify(chat),
        });
        if (!response.ok) {
          const data = await readResponse(response);
          throw new Error(data.detail ?? `儲存聊天室失敗 (${response.status})`);
        }
      })
      .catch(error => console.error("Unable to save chatroom", error));
  }

  function persistChatHistory(update:(current:StoredChat[]) => StoredChat[]) {
    setChatHistory(current => {
      const next = update(current).slice(0,30);
      next.forEach(queueChatSave);
      return next;
    });
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const response = await fetch(`${API}/chatrooms`);
        const data = await readResponse(response);
        if (!response.ok) throw new Error(data.detail ?? `讀取聊天室失敗 (${response.status})`);
        if (active) setChatHistory(data);
      } catch (error) {
        console.error("Unable to load chatrooms", error);
        if (active) setChatHistory([]);
      }
    })();
    return () => { active = false; };
  }, []);

  function patchStoredGeneration(chatId:string, exchangeId:string, changes:Partial<GenerationExchange>) {
    persistChatHistory(current => current.map(chat => chat.id === chatId ? {
      ...chat,
      generationExchanges:chat.generationExchanges.map(exchange => exchange.id === exchangeId ? {...exchange,...changes} : exchange),
    } : chat));
  }

  function patchStoredRevision(chatId:string, exchangeId:string, changes:Partial<RevisionExchange>) {
    persistChatHistory(current => current.map(chat => chat.id === chatId ? {
      ...chat,
      revisionExchanges:chat.revisionExchanges.map(exchange => exchange.id === exchangeId ? {...exchange,...changes} : exchange),
    } : chat));
  }

  function updateStoredImage(oldId:string, value:ImageRecord) {
    persistChatHistory(current => current.map(chat => ({
      ...chat,
      revisionExchanges:chat.revisionExchanges.map(exchange => exchange.image?.id === oldId ? {...exchange,image:value} : exchange),
      generationExchanges:chat.generationExchanges.map(exchange => ({...exchange,images:exchange.images.map(image => image.id === oldId ? value : image)})),
    })));
  }
  useEffect(() => {
    if (!showElements) return;
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === "Escape") closeElementSheet(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [showElements]);
  const updateImage = (oldId:string, value:ImageRecord) => {
    setRevisionExchanges(current => current.map(exchange => exchange.image?.id === oldId ? {...exchange,image:value} : exchange));
    setGenerationExchanges(current => current.map(exchange => ({...exchange,images:exchange.images.map(image => image.id === oldId ? value : image)})));
    updateStoredImage(oldId, value);
  };

  function updateGalleryAsset(recordId:string, assetType:AssetType, changes:Partial<Pick<GalleryAsset,"saved"|"favorite"|"collection_ids">>) {
    const matches = (asset:GalleryAsset) => asset.record_id === recordId && asset.asset_type === assetType;
    setAllImages(current => current.map(asset => matches(asset) ? {...asset,...changes} : asset));
    setFavoriteImages(current => current.map(asset => matches(asset) ? {...asset,...changes} : asset).filter(asset => activeCollection ? asset.collection_ids?.includes(activeCollection.id) ?? asset.favorite : asset.favorite));
  }

  useEffect(() => {
    if (!activeChatId || !conversationStarted) return;
    const chat:StoredChat = {
      id:activeChatId,
      title:generationExchanges[0]?.prompt || generationExchanges[0]?.elements.join("、") || "圖騰對話",
      revisionExchanges, generationExchanges,
    };
    setChatHistory(current => {
      const next = [chat, ...current.filter(item => item.id !== activeChatId)].slice(0,30);
      queueChatSave(chat);
      return next;
    });
  }, [activeChatId, conversationStarted, generationExchanges, revisionExchanges]);

  function newChat() {
    setConversationStarted(false); setActiveChatId(null);
    setRevisionExchanges([]); setGenerationExchanges([]); setRevisionTarget(null); setPrompt("");
    setStatus("每次生成一個圖騰，再輸出圖案相同的 4 組配色。"); setTopbarScrolled(false); setPage("chat"); setSidebarOpen(false);
  }

  function displayChat(chat:StoredChat) {
    setActiveChatId(chat.id); setRevisionExchanges(chat.revisionExchanges); setGenerationExchanges(chat.generationExchanges.map(normalizeGenerationExchange));
    setConversationStarted(true); setRevisionTarget(null); setTopbarScrolled(false); setPage("chat"); setSidebarOpen(false);
  }

  async function openChat(chat:StoredChat) {
    setSidebarOpen(false);
    try {
      const refreshed = await requestChatroom(chat.id);
      setChatHistory(current => [refreshed,...current.filter(item => item.id !== refreshed.id)].slice(0,30));
      displayChat(refreshed);
    } catch (error) {
      displayChat(chat);
      setStatus(error instanceof Error ? error.message : "讀取聊天室失敗");
    }
  }

  async function openFavorites() {
    setActiveCollection(null); setTopbarScrolled(false); setPage("favorites"); setSidebarOpen(false);
    const response = await fetch(`${API}/images/collections`);
    const data = await readResponse(response);
    const folders:CollectionRecord[] = response.ok ? data : [];
    const foldersWithPreviews = await Promise.all(folders.map(async folder => {
      const assetsResponse = await fetch(`${API}/images/collections/${folder.id}/assets`);
      if (!assetsResponse.ok) return folder;
      const assets:GalleryAsset[] = await readResponse(assetsResponse);
      const previewUrls = [...assets]
        .sort((left,right) => new Date(right.created_at).getTime()-new Date(left.created_at).getTime())
        .slice(0,3)
        .map(asset => asset.url);
      return {...folder,preview_urls:previewUrls};
    }));
    setCollectionFolders(foldersWithPreviews);
  }

  async function openCollection(collection:CollectionRecord) {
    const response = await fetch(`${API}/images/collections/${collection.id}/assets`);
    const data = await readResponse(response);
    setFavoriteImages(response.ok ? data : []); setTopbarScrolled(false); setActiveCollection(collection);
  }

  async function addCollectionFolder() {
    const name = folderName.trim();
    if (!name) return;
    const response = await fetch(`${API}/images/collections`, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
    const data = await readResponse(response);
    if (response.ok) { setCollectionFolders(current => [...current,data]); setFolderName(""); }
  }

  async function openImages() {
    const response = await fetch(`${API}/images/assets`);
    const data = await readResponse(response);
    if (!response.ok) {
      setStatus(data.detail ?? `讀取圖片失敗 (${response.status})`);
      setSidebarOpen(false);
      return;
    }
    setAllImages(data); setTopbarScrolled(false); setPage("images"); setSidebarOpen(false);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!prompt.trim() && (!revisionTarget ? selected.length === 0 : revisionMode === "elements")) return;
    const revisionInstruction = prompt.trim() || (revisionMode === "palette" ? "隨機更換配色" : "原組合重新生成");
    const payload: GenerateRequest = { prompt, elements: selected };
    setPrompt(""); setSelected([]); setShowElements(false);
    if (revisionTarget) {
      const target = revisionTarget;
      const exchangeId = `${target.id}-${Date.now()}`;
      const chatId = activeChatId;
      setConversationStarted(true); setBusy(true); setRevisionTarget(null);
      const modeLabel = revisionMode === "palette" ? "更換配色" : revisionMode === "elements" ? "更換元素" : revisionMode === "product" ? "更換商品圖" : "原組合重新生成";
      const productDescription = `${revisionProduct}・${revisionPlacement}・${revisionDisplayStyle}`;
      const pendingRevision:RevisionExchange = { id:exchangeId, createdAt:Date.now(), user:revisionMode === "product" ? `${modeLabel}：${productDescription}` : `${modeLabel}${prompt.trim() ? `：${prompt.trim()}` : ""}`, sourceImage:target.totem_url ?? target.url, reply:revisionMode === "product" ? "正在把同一個圖騰套用到新的商品設定…" : revisionMode === "palette" ? "正在以程式演算法更換配色…" : "正在依照你的要求修改這張圖騰…", pending:true };
      setRevisionExchanges(current => [...current, pendingRevision]);
      if (chatId) persistChatHistory(current => current.map(chat => chat.id === chatId ? {...chat,revisionExchanges:[...chat.revisionExchanges,pendingRevision]} : chat));
      try {
        let data:ImageRecord;
        if (revisionMode === "product") {
          data = await requestProtectedImage(`${API}/images/${target.id}/preview/variant`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({product:revisionProduct,placement:revisionPlacement,display_style:revisionDisplayStyle}) }, chatId ?? undefined, exchangeId);
        } else {
          data = await requestProtectedImage(`${API}/images/${target.id}/regenerate`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({instruction:revisionInstruction,mode:revisionMode}) }, chatId ?? undefined, exchangeId);
        }
        const completed:Partial<RevisionExchange> = {reply:revisionMode === "product" ? "新的商品圖已完成；圖騰本身保持不變。" : "已依照你的要求產生新的圖騰；原圖與商品預覽都已保留。",image:data,pending:false};
        setRevisionExchanges(current => current.map(exchange => exchange.id === exchangeId ? {...exchange,...completed} : exchange));
        if (chatId) patchStoredRevision(chatId, exchangeId, completed);
      } catch (error) {
        const message = error instanceof Error ? error.message : "修改失敗";
        setRevisionExchanges(current => current.map(exchange => exchange.id === exchangeId ? {...exchange,reply:message,pending:false} : exchange));
        if (chatId) patchStoredRevision(chatId, exchangeId, {reply:message,pending:false});
      } finally { setBusy(false); }
      return;
    }

    {
      const exchangeId = `generation-${Date.now()}`;
      const chatId = activeChatId ?? `${Date.now()}`;
      const pendingExchange:GenerationExchange = {
        id:exchangeId,
        createdAt:Date.now(),
        prompt:payload.prompt.trim(),
        elements:[...payload.elements],
        reply:"正在理解你的想法並生成四組配色…",
        images:[],
        pending:true,
      };
      setConversationStarted(true);
      setActiveChatId(chatId);
      setGenerationExchanges(current => [...current, pendingExchange]);
      const title = generationExchanges[0]?.prompt || generationExchanges[0]?.elements.join("、") || pendingExchange.prompt || pendingExchange.elements.join("、") || "圖騰對話";
      const pendingChat:StoredChat = {
        id:chatId,
        title,
        revisionExchanges:[...revisionExchanges],
        generationExchanges:[...generationExchanges,pendingExchange],
      };
      // The chat exists synchronously with the first submitted message, before
      // waiting for the image API response.
      persistChatHistory(current => [pendingChat,...current.filter(chat => chat.id !== chatId)]);
      setBusy(true);
      try {
        const data = await requestImageGeneration(payload, crypto.randomUUID(), chatId, exchangeId);
        const completedExchange:Partial<GenerationExchange> = {
          reply:`完成了！這是相同圖案的 ${data.images.length} 組配色。`,
          images:data.images,
          pending:false,
        };
        setGenerationExchanges(current => current.map(exchange => exchange.id === exchangeId ? {
          ...exchange,
          ...completedExchange,
        } : exchange));
        patchStoredGeneration(chatId, exchangeId, completedExchange);
      } catch (error) {
        try {
          const refreshed = await requestChatroom(chatId);
          const recovered = refreshed.generationExchanges.find(exchange => exchange.id === exchangeId);
          if (recovered && !recovered.pending) {
            setChatHistory(current => [refreshed,...current.filter(chat => chat.id !== refreshed.id)].slice(0,30));
            setGenerationExchanges(current => current.map(exchange => exchange.id === exchangeId ? normalizeGenerationExchange(recovered) : exchange));
            return;
          }
        } catch {
          // Keep the original request error when reconciliation also cannot reach the server.
        }
        const message = error instanceof Error ? error.message : "生成失敗";
        setGenerationExchanges(current => current.map(exchange => exchange.id === exchangeId ? {...exchange,reply:message,pending:false} : exchange));
        patchStoredGeneration(chatId, exchangeId, {reply:message,pending:false});
      } finally { setBusy(false); }
      return;
    }
  }

  async function regenerateGeneration(exchange:GenerationExchange) {
    if (busy || exchange.pending || exchange.images.length !== 4) return;
    const chatId=activeChatId??`${Date.now()}`;
    const exchangeId=`generation-regeneration-${Date.now()}`;
    const pending:GenerationExchange={id:exchangeId,createdAt:Date.now(),prompt:exchange.prompt,elements:[...exchange.elements],reply:"正在依照原提示重新生成 4 張圖騰…",images:[],pending:true,hideUserMessage:true};
    setBusy(true);
    setActiveChatId(chatId);
    setGenerationExchanges(current=>[...current,pending]);
    persistChatHistory(current=>current.map(chat=>chat.id===chatId?{...chat,generationExchanges:[...chat.generationExchanges,pending]}:chat));
    window.requestAnimationFrame(()=>{
      const chat=document.querySelector<HTMLElement>(".hero");
      chat?.scrollTo({top:chat.scrollHeight,behavior:"smooth"});
    });
    try {
      const data=await requestImageGeneration(
        {prompt:exchange.prompt,elements:[...exchange.elements]},
        crypto.randomUUID(),
        chatId,
        exchangeId,
      );
      const completed:Partial<GenerationExchange>={reply:`完成了！這是相同圖案的 ${data.images.length} 組配色。`,images:data.images,pending:false};
      setGenerationExchanges(current=>current.map(item=>item.id===exchangeId?{...item,...completed}:item));
      patchStoredGeneration(chatId,exchangeId,completed);
      window.requestAnimationFrame(()=>{
        const chat=document.querySelector<HTMLElement>(".hero");
        chat?.scrollTo({top:chat.scrollHeight,behavior:"smooth"});
      });
    } catch (error) {
      const failed:Partial<GenerationExchange>={reply:error instanceof Error?error.message:"重新生成失敗。",pending:false};
      setGenerationExchanges(current=>current.map(item=>item.id===exchangeId?{...item,...failed}:item));
      patchStoredGeneration(chatId,exchangeId,failed);
    } finally { setBusy(false); }
  }

  function startRevision(image:ImageRecord) {
    setRevisionTarget(image); setRevisionMode("same"); setPrompt(""); setSelected([]); setShowElements(false);
    setStatus("請在下方輸入想如何修改這張圖騰。");
    setTimeout(() => promptInput.current?.focus(), 0);
  }

  function closeElementSheet() {
    setShowElements(false);
    setElementSheetDrag(0);
  }

  function startElementSheetDrag(event: React.PointerEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest("button")) return;
    elementSheetStartY.current = event.clientY;
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveElementSheetDrag(event: React.PointerEvent<HTMLDivElement>) {
    if (elementSheetStartY.current === null) return;
    setElementSheetDrag(Math.max(0, event.clientY - elementSheetStartY.current));
  }

  function endElementSheetDrag() {
    if (elementSheetDrag > 90) closeElementSheet();
    else setElementSheetDrag(0);
    elementSheetStartY.current = null;
  }

  const toggle = (name: string) => setSelected(values => values.includes(name) ? values.filter(value => value !== name) : [...values, name]);
  const timelineExchanges = [
    ...revisionExchanges.map(exchange => ({kind:"revision" as const, createdAt:(exchange.createdAt ?? Number(exchange.id.split("-").at(-1))) || 0, exchange})),
    ...generationExchanges.map(value => {const exchange=normalizeGenerationExchange(value);return {kind:"generation" as const, createdAt:(exchange.createdAt ?? Number(exchange.id.split("-").at(-1))) || 0, exchange};}),
  ].sort((left,right) => left.createdAt - right.createdAt);
  return <div className="app-shell">
    <header className={`topbar ${page !== "chat" ? "topbar-tall" : ""} ${topbarScrolled ? "scrolled" : ""}`}>{page === "favorites" && activeCollection ? <button type="button" onClick={openFavorites} aria-label="返回我的收藏"><BackIcon /></button> : <button type="button" onClick={() => setSidebarOpen(true)} aria-label="開啟功能列"><MenuIcon /></button>}{page !== "chat" && <><div className="topbar-copy"><strong className="topbar-title">{page === "images" ? "我的圖片" : activeCollection?.name ?? "我的收藏"}</strong><small>圖片只保留 14 天</small></div><button type="button" className="topbar-new-chat" onClick={newChat} aria-label="開始新對話"><NewChatIcon /></button></>}</header>
    {sidebarOpen && <><button className="drawer-backdrop" type="button" onClick={() => setSidebarOpen(false)} aria-label="關閉功能列"/><aside className="side-drawer">
      <div className="drawer-heading"><strong>AI</strong><button type="button" className="close-image-button" onClick={() => setSidebarOpen(false)} aria-label="關閉功能列"><CloseButtonIcon /></button></div>
      <nav className="drawer-menu">
        <button type="button" onClick={newChat}><span><NewChatIcon /></span>新對話</button>
        <button type="button" onClick={openImages}><span><ImagesIcon /></span>我的圖片</button>
        <button type="button" onClick={openFavorites}><span><BookmarkIcon /></span>我的收藏</button>
      </nav>
      <div className="recent-chats"><p>最近對話</p>{chatHistory.length === 0 ? <small>尚無對話紀錄</small> : chatHistory.map(chat => <button type="button" className={chat.id === activeChatId ? "active" : ""} onClick={() => void openChat(chat)} key={chat.id}>{chat.title}</button>)}</div>
      <button type="button" className="drawer-logout" onClick={()=>void onLogout()}>登出</button>
    </aside></>}

    <main className="workspace">
      {page === "favorites" ? <section className="favorites-page" onScroll={event => setTopbarScrolled(event.currentTarget.scrollTop > 8)}>{activeCollection ? favoriteImages.length === 0 ? <p className="favorites-empty">這個資料夾還沒有圖片。</p> : <div className="favorites-grid">{favoriteImages.map(asset => <GalleryAssetCard asset={asset} onChanged={updateGalleryAsset} key={`${asset.record_id}-${asset.asset_type}`}/>)}</div> : <div className="collection-folder-grid">{collectionFolders.map(folder => <button type="button" className="collection-folder-card" onClick={() => openCollection(folder)} key={folder.id}><CollectionCover urls={folder.preview_urls ?? (folder.preview_url ? [folder.preview_url] : [])}/><strong>{folder.name}</strong><small>{folder.image_count} 張圖片</small></button>)}<form className="collection-create-card" onSubmit={event => {event.preventDefault();void addCollectionFolder();}}><div className="collection-create-cover"><i/><i/><i/><button type="submit">建立</button></div><input value={folderName} onChange={event => setFolderName(event.target.value)} aria-label="新資料夾名稱" placeholder="資料夾名稱"/></form></div>}</section> : page === "images" ? <section className="favorites-page images-page" onScroll={event => setTopbarScrolled(event.currentTarget.scrollTop > 8)}>{allImages.length === 0 ? <p className="favorites-empty">還沒有圖片。</p> : <div className="favorites-grid">{allImages.map(asset => <GalleryAssetCard asset={asset} onChanged={updateGalleryAsset} key={`${asset.record_id}-${asset.asset_type}`}/>)}</div>}</section> : <section className="hero" onScroll={event => setTopbarScrolled(event.currentTarget.scrollTop > 8)}>
        {!conversationStarted && <div className="hero-intro"><h1>你說，我畫！</h1><p>選擇元素或描述想法，開始設計圖騰。</p></div>}
        {conversationStarted && <div className="chat-thread">
          {timelineExchanges.map(item => item.kind === "revision" ? <div className="revision-exchange" key={item.exchange.id}>
            <div className="message user-message revision-user-message"><img src={`${SERVER}${item.exchange.sourceImage}`} alt="這次要求修改的原圖騰"/><p>{item.exchange.user}</p></div>
            <div className={`message ai-message ${item.exchange.pending ? "thinking" : ""}`}><div className="ai-mark">AI</div><p>{item.exchange.reply}</p>{(item.exchange.pending || item.exchange.image) && <div className="chat-results"><div className="gallery">{item.exchange.image ? <ImageCard image={item.exchange.image} updateImage={updateImage} setStatus={setStatus} askRegenerate={startRevision}/> : <div className="generation-placeholder" aria-hidden="true"/>}</div></div>}</div>
          </div> : <div className="revision-exchange" key={item.exchange.id}>
            {!item.exchange.hideUserMessage && <div className="message user-message">{item.exchange.elements.length > 0 && <div className="message-tags">{item.exchange.elements.map(name => <span key={name}><ElementTagIcon name={name}/>{name}</span>)}</div>}{item.exchange.prompt && <p>{item.exchange.prompt}</p>}</div>}
            <div className={`message ai-message ${item.exchange.pending ? "thinking" : ""}`}><div className="ai-mark">AI</div><p>{item.exchange.reply}</p>{(item.exchange.pending || item.exchange.images.length > 0) && <div className="chat-results"><div className="gallery">{item.exchange.images.length > 0 ? item.exchange.images.map(image => <ImageCard image={image} updateImage={updateImage} setStatus={setStatus} askRegenerate={startRevision} key={image.id}/>) : Array.from({length:4},(_,index)=><div className="generation-placeholder" aria-hidden="true" key={index}/>)}</div>{item.exchange.images.length === 4 && <div className="generation-regenerate"><span>一鍵重新生成</span><button type="button" disabled={busy || item.exchange.pending} onClick={()=>void regenerateGeneration(item.exchange)} aria-label="依照原提示重新生成"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 8a8 8 0 1 0 1 6"/><path d="M19 3v5h-5"/></svg></button></div>}</div>}</div>
          </div>)}
        </div>}
        <form className="composer" onSubmit={submit}>
          {revisionTarget && <><div className="revision-context"><img src={`${SERVER}${revisionTarget.totem_url ?? revisionTarget.url}`} alt="要修改的圖騰"/><div><strong>{revisionMode === "product" ? "更換商品圖" : "修改圖騰"}</strong><span>{revisionMode === "product" ? "選擇商品、圖騰位置與商品顏色" : revisionMode === "palette" ? "可直接送出隨機換色，或輸入指定顏色" : "描述你想如何修改這張圖騰"}</span></div><button type="button" className="close-image-button" onClick={() => setRevisionTarget(null)} aria-label="取消修改"><CloseButtonIcon /></button></div><div className="revision-mode-tags"><button type="button" className={revisionMode === "elements" ? "active" : ""} onClick={() => setRevisionMode("elements")}>更換元素</button><button type="button" className={revisionMode === "palette" ? "active" : ""} onClick={() => setRevisionMode("palette")}>更換配色</button><button type="button" className={revisionMode === "same" ? "active" : ""} onClick={() => setRevisionMode("same")}>原組合重新生成</button><button type="button" className={revisionMode === "product" ? "active" : ""} onClick={() => setRevisionMode("product")}>更換商品圖</button></div>{revisionMode === "product" && <div className="product-revision-options"><label>載體<select value={revisionProduct} onChange={event => {const value=event.target.value;setRevisionProduct(value);setRevisionPlacement(placementByProduct[value][0]);}}>{products.map(value => <option value={value} key={value}>{value}</option>)}</select></label><label>圖騰位置<select value={revisionPlacement} onChange={event => setRevisionPlacement(event.target.value)}>{placementByProduct[revisionProduct].map(value => <option value={value} key={value}>{value}</option>)}</select></label><label>商品與背景<select value={revisionDisplayStyle} onChange={event => setRevisionDisplayStyle(event.target.value)}><option>白色商品＋白底</option><option>黑色商品＋白底</option><option>深紅色商品＋白底</option><option>深綠色商品＋白底</option><option>深藍色商品＋白底</option></select></label></div>}</>}
          {selected.length > 0 && <div className="composer-tags">{selected.map(name => <button type="button" onClick={() => toggle(name)} key={name}><ElementTagIcon name={name}/>{name}<span>×</span></button>)}</div>}
          <div className={`prompt-row ${revisionTarget && revisionMode === "product" ? "product-submit-row" : ""}`}>
            {(!revisionTarget || revisionMode !== "product") &&
            <input ref={promptInput} aria-label="想表達的圖案" value={prompt} onChange={event => setPrompt(event.target.value)} placeholder={revisionTarget ? (revisionMode === "palette" ? "例如：把紅色換成綠色（可留空隨機）" : revisionMode === "elements" ? "例如：拿掉月亮，加入山豬" : "可輸入補充要求，或直接送出") : "請描述你想設計的圖案..."} />
            }<button className="send-button" disabled={busy} aria-label={revisionTarget && revisionMode === "product" ? "生成新的商品圖" : revisionTarget ? "送出修改要求" : "生成 4 組隨機配色"}>{busy ? "…" : revisionTarget && revisionMode === "product" ? "生成商品圖" : "↑"}</button>
          </div>
          {!revisionTarget && <><div className="tool-row">
            <button type="button" className={showElements ? "tool-active" : ""} onClick={() => showElements ? closeElementSheet() : setShowElements(true)}><span><ElementsIcon /></span>元素{selected.length > 0 && <b>{selected.length}</b>}</button>
            <button type="button" disabled><span>◫</span>風格</button>
            <button type="button" disabled><span>⌕</span>工藝技術</button>
          </div>
          </>}
        </form>
        {showElements && <div className="element-sheet-background" aria-hidden="true"/>}
        {showElements && <section className="element-sheet" style={{transform:`translate(-50%, ${elementSheetDrag}px)`}} role="dialog" aria-label="選擇元素">
          <div className="element-sheet-header" onPointerDown={startElementSheetDrag} onPointerMove={moveElementSheetDrag} onPointerUp={endElementSheetDrag} onPointerCancel={endElementSheetDrag}>
            <span className="element-sheet-handle" aria-hidden="true"/>
            <div><strong>選擇元素</strong><small>點選想加入圖騰的元素</small></div>
            <button type="button" className="close-image-button" onPointerDown={event => event.stopPropagation()} onClick={closeElementSheet} aria-label="關閉元素選擇"><CloseButtonIcon /></button>
          </div>
          <div className="element-grid">{elementNames.map(name => <button type="button" className={selected.includes(name) ? "active" : ""} onClick={() => toggle(name)} aria-label={name} aria-pressed={selected.includes(name)} key={name}><img src={elementImages[name] ?? fallbackElementImage} alt="" /></button>)}</div>
        </section>}
      </section>}
    </main>
    {page !== "chat" && <nav className={`page-switch page-switch-${page}`} aria-label="快速切換圖片與收藏" onClickCapture={event => {if(pageSwitchDidSwipe.current){event.preventDefault();event.stopPropagation();pageSwitchDidSwipe.current=false;}}} onPointerDown={event => {pageSwitchStartX.current=event.clientX;pageSwitchDidSwipe.current=false;}} onPointerUp={event => {const start=pageSwitchStartX.current;pageSwitchStartX.current=null;if(start===null)return;const distance=event.clientX-start;if(distance < -24){pageSwitchDidSwipe.current=true;void openFavorites();}else if(distance > 24){pageSwitchDidSwipe.current=true;void openImages();}}} onPointerLeave={() => {pageSwitchStartX.current=null;}} onPointerCancel={() => {pageSwitchStartX.current=null;pageSwitchDidSwipe.current=false;}}><span className="page-switch-slider" aria-hidden="true"/><button type="button" className={page==="images"?"active":""} onClick={openImages} aria-label="切換到我的圖片頁面" aria-current={page==="images"?"page":undefined}><ImagesIcon /></button><button type="button" className={page==="favorites"?"active":""} onClick={openFavorites} aria-label="切換到我的收藏頁面" aria-current={page==="favorites"?"page":undefined}><BookmarkIcon /></button></nav>}
  </div>;
}

export type PreviewRequest = { 
    product:string; 
    placement:string; 
    display_style:string 
};
export type ImageRecord = { 
    id:string; 
    created_at:string;
    expires_at:string;
    url:string; 
    original_url?:string; 
    totem_url?:string; 
    palette_name?:string; 
    generation?:{elements?:string[]}; 
    request?:{elements?:string[]} 
    assets?: Partial<Record<AssetType, ImageAsset>>;
};
export type GenerateRequest = { 
    prompt:string; 
    elements:string[] 
};

export type AssetType = "motif" | "preview" | "chart";

export type ImageAsset = {
  type: AssetType;
  filename?: string;
  url?: string;
  saved: boolean;
  favorite: boolean;
  collection_ids?: string[];
  parameters?: Partial<PreviewRequest & {
    width?: number;
    height?: number;
    colors?: number;
  }>;
};

export type GalleryAsset = {
  record_id: string;
  asset_type: AssetType;
  url: string;
  saved: boolean;
  favorite: boolean;
  collection_ids?: string[];
  created_at: string;
  expires_at: string;
  elements: string[];
  width?: number;
  height?: number;
};

export type CollectionRecord = {
  id: string;
  name: string;
  system: boolean;
  image_count: number;
  preview_url?: string;
  preview_urls?: string[];
};

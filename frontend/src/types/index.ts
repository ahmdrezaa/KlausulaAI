export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Array<{
    pasal: string;
    uu: string;
  }>;
}

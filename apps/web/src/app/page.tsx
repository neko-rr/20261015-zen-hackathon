import { Studio } from "@/components/Studio";

// ログイン前の HTML を1年キャッシュすると、確認中の画面だけが残る。
export const dynamic = "force-dynamic";

export default function Page() {
  return <Studio />;
}

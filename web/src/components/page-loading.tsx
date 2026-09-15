import Image from "next/image";

export function PageLoading() {
  return <div className="route-loading page-loading" role="status" aria-live="polite" aria-busy="true"><span className="loading-mark"><Image src="/brand/assetguard-mark.svg" alt="MaintainNexus AI" width={56} height={56} priority /></span><p>Gathering the latest station story...</p></div>;
}

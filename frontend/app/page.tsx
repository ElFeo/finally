import dynamic from 'next/dynamic';

const TradingWorkstation = dynamic(
  () => import('@/components/TradingWorkstation'),
  { ssr: false }
);

export default function Page() {
  return <TradingWorkstation />;
}

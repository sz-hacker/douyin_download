import { Toaster } from './components/ui/sonner';
import { VideoDownloader } from './components/video-downloader';

export default function App() {
  return (
    <div className="size-full">
      <VideoDownloader />
      <Toaster 
        theme="dark"
        toastOptions={{
          style: {
            background: '#000',
            border: '1px solid rgba(34, 197, 94, 0.3)',
            color: '#4ade80',
            fontFamily: 'monospace'
          }
        }}
      />
    </div>
  );
}

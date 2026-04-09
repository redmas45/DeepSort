import { useEffect, useRef } from "react";

type VideoCanvasProps = {
  frameData: string;
};

export function VideoCanvas({ frameData }: VideoCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!frameData || !canvasRef.current) {
      return;
    }

    const context = canvasRef.current.getContext("2d");
    if (!context) {
      return;
    }

    const image = new Image();
    image.onload = () => {
      if (!canvasRef.current) {
        return;
      }
      canvasRef.current.width = image.width;
      canvasRef.current.height = image.height;
      context.drawImage(image, 0, 0);
    };
    image.src = frameData;
  }, [frameData]);

  return (
    <div className="panel frame-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Client</p>
          <h2>React canvas</h2>
        </div>
      </div>
      <canvas className="video-canvas" ref={canvasRef} />
      {!frameData ? (
        <div className="empty-state">
          The live frame will appear here after the WebSocket stream starts.
        </div>
      ) : null}
    </div>
  );
}

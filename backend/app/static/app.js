(function () {
  const state = {
    mode: "camera",
    socket: null,
    mediaStream: null,
    captureVideo: null,
    captureCanvas: null,
    captureContext: null,
    captureTimer: null,
    awaitingFrame: false,
  };

  const cameraModeButton = document.getElementById("cameraModeButton");
  const videoModeButton = document.getElementById("videoModeButton");
  const cameraFacingSelect = document.getElementById("cameraFacingSelect");
  const videoSourceSelect = document.getElementById("videoSourceSelect");
  const videoUploadInput = document.getElementById("videoUploadInput");
  const uploadField = document.getElementById("uploadField");
  const startButton = document.getElementById("startButton");
  const stopButton = document.getElementById("stopButton");
  const modeHint = document.getElementById("modeHint");
  const feedbackText = document.getElementById("feedbackText");
  const statusChip = document.getElementById("statusChip");
  const frameCanvas = document.getElementById("frameCanvas");
  const emptyState = document.getElementById("emptyState");
  const fpsValue = document.getElementById("fpsValue");
  const objectCountValue = document.getElementById("objectCountValue");
  const frameIndexValue = document.getElementById("frameIndexValue");
  const activeCountPill = document.getElementById("activeCountPill");
  const trackList = document.getElementById("trackList");
  const frameContext = frameCanvas.getContext("2d");

  function setStatus(status, message) {
    statusChip.textContent = status;
    statusChip.className = `status-chip status-${status}`;
    if (message) {
      feedbackText.textContent = message;
    }
  }

  function setMode(mode) {
    state.mode = mode;
    const isCamera = mode === "camera";
    cameraModeButton.classList.toggle("mode-chip-active", isCamera);
    videoModeButton.classList.toggle("mode-chip-active", !isCamera);
    cameraFacingSelect.disabled = !isCamera;
    videoSourceSelect.disabled = isCamera;
    uploadField.classList.toggle("hidden", isCamera);
    startButton.textContent = isCamera ? "Enable camera tracking" : "Start video stream";
    modeHint.textContent = isCamera
      ? "Camera permission is requested in the browser, then frames are streamed to FastAPI for tracking."
      : "Use your uploaded videos to test the same tracking pipeline without a live camera.";
  }

  function renderTracks(tracks) {
    activeCountPill.textContent = `${tracks.length} active`;
    if (!tracks.length) {
      trackList.innerHTML = '<p class="muted">No tracked people yet.</p>';
      return;
    }

    trackList.innerHTML = tracks
      .map(
        (track) => `
          <article class="track-card">
            <div class="track-card-row">
              <strong>ID ${track.track_id}</strong>
              <span>${track.class_name}</span>
            </div>
            <div class="track-card-row">
              <span>confidence ${Number(track.confidence).toFixed(2)}</span>
              <span>velocity ${Number(track.velocity_px[0]).toFixed(1)}, ${Number(track.velocity_px[1]).toFixed(1)}</span>
            </div>
          </article>
        `,
      )
      .join("");
  }

  function renderStats(stats) {
    fpsValue.textContent = stats ? String(stats.fps) : "--";
    objectCountValue.textContent = stats ? String(stats.object_count) : "--";
    frameIndexValue.textContent = stats ? String(stats.frame_index) : "--";
  }

  function renderFrame(base64Frame) {
    if (!base64Frame) {
      return;
    }

    const image = new Image();
    image.onload = () => {
      frameCanvas.width = image.width;
      frameCanvas.height = image.height;
      frameContext.drawImage(image, 0, 0);
      emptyState.classList.add("hidden");
    };
    image.src = `data:image/jpeg;base64,${base64Frame}`;
  }

  function cleanupCamera() {
    if (state.captureTimer) {
      window.clearInterval(state.captureTimer);
      state.captureTimer = null;
    }
    if (state.mediaStream) {
      state.mediaStream.getTracks().forEach((track) => track.stop());
      state.mediaStream = null;
    }
    state.captureVideo = null;
    state.captureCanvas = null;
    state.captureContext = null;
    state.awaitingFrame = false;
  }

  function disconnect() {
    state.awaitingFrame = false;
    if (state.socket && state.socket.readyState === WebSocket.OPEN && state.mode === "camera") {
      state.socket.send(JSON.stringify({ event: "stop" }));
    }
    if (state.socket) {
      state.socket.close();
      state.socket = null;
    }
    cleanupCamera();
    setStatus("closed", "Tracking stopped.");
  }

  function buildWebSocketUrl(path, params) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = new URL(`${protocol}//${window.location.host}${path}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
    }
    return url.toString();
  }

  function bindSocket(socket) {
    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);

      if (payload.event === "frame") {
        state.awaitingFrame = false;
        renderFrame(payload.frame);
        renderTracks(payload.tracks || []);
        renderStats(payload.stats || null);
        return;
      }

      if (payload.event === "ready") {
        setStatus("live", payload.message || "Camera stream ready.");
        return;
      }

      if (payload.event === "end") {
        state.awaitingFrame = false;
        setStatus("closed", `Stream finished for ${payload.video_name || "current source"}.`);
        return;
      }

      state.awaitingFrame = false;
      setStatus("error", payload.message || "Unexpected stream error.");
    };

    socket.onerror = () => {
      state.awaitingFrame = false;
      setStatus("error", "WebSocket connection failed.");
    };

    socket.onclose = () => {
      state.awaitingFrame = false;
      if (state.socket === socket) {
        state.socket = null;
      }
      cleanupCamera();
    };
  }

  function startCameraPump(socket) {
    state.captureCanvas = document.createElement("canvas");
    state.captureContext = state.captureCanvas.getContext("2d");

    state.captureTimer = window.setInterval(() => {
      if (!state.captureVideo || !state.captureContext) {
        return;
      }
      if (socket.readyState !== WebSocket.OPEN || !state.captureVideo.videoWidth || !state.captureVideo.videoHeight) {
        return;
      }
      if (state.awaitingFrame) {
        return;
      }

      const scale = Math.min(1, 960 / state.captureVideo.videoWidth);
      state.captureCanvas.width = Math.round(state.captureVideo.videoWidth * scale);
      state.captureCanvas.height = Math.round(state.captureVideo.videoHeight * scale);
      state.captureContext.drawImage(
        state.captureVideo,
        0,
        0,
        state.captureCanvas.width,
        state.captureCanvas.height,
      );

      state.awaitingFrame = true;
      socket.send(
        JSON.stringify({
          event: "frame",
          frame: state.captureCanvas.toDataURL("image/jpeg", 0.72),
        }),
      );
    }, 200);
  }

  async function fetchSources() {
    try {
      const response = await fetch("/api/videos");
      if (!response.ok) {
        throw new Error("Unable to load video sources.");
      }

      const data = await response.json();
      const sources = data.sources || [];
      videoSourceSelect.innerHTML = "";
      sources.forEach((source) => {
        const option = document.createElement("option");
        option.value = source.name;
        option.textContent = source.name;
        videoSourceSelect.appendChild(option);
      });

      feedbackText.textContent = `Loaded ${sources.length} available sources.`;
    } catch (error) {
      setStatus("error", error instanceof Error ? error.message : "Unable to load video sources.");
    }
  }

  async function uploadVideo(file) {
    const formData = new FormData();
    formData.append("file", file);
    setStatus("connecting", "Uploading video...");

    const response = await fetch("/api/videos/upload", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to upload video.");
    }

    await fetchSources();
    if (payload.source && payload.source.name) {
      videoSourceSelect.value = payload.source.name;
    }
    setStatus("closed", payload.message || "Video uploaded.");
  }

  function startVideoStream() {
    disconnect();
    const selectedSource = videoSourceSelect.value;
    if (!selectedSource) {
      setStatus("error", "Select a video source first.");
      return;
    }

    setStatus("connecting", `Connecting to ${selectedSource}...`);
    const socket = new WebSocket(buildWebSocketUrl("/ws/stream", { video: selectedSource }));
    state.socket = socket;

    socket.onopen = () => {
      setStatus("live", `Streaming ${selectedSource}`);
    };

    bindSocket(socket);
  }

  async function startCameraStream() {
    disconnect();
    setStatus("connecting", "Requesting camera access...");

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus("error", "This browser does not support camera capture.");
      return;
    }

    try {
      let mediaStream;
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: cameraFacingSelect.value },
          audio: false,
        });
      } catch {
        mediaStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      }

      const captureVideo = document.createElement("video");
      captureVideo.srcObject = mediaStream;
      captureVideo.muted = true;
      captureVideo.playsInline = true;
      await captureVideo.play();

      state.mediaStream = mediaStream;
      state.captureVideo = captureVideo;

      const socket = new WebSocket(buildWebSocketUrl("/ws/live-camera"));
      state.socket = socket;

      socket.onopen = () => {
        setStatus("live", "Camera tracking is live.");
        startCameraPump(socket);
      };

      bindSocket(socket);
    } catch (error) {
      cleanupCamera();
      setStatus("error", error instanceof Error ? error.message : "Unable to access the camera.");
    }
  }

  cameraModeButton.addEventListener("click", () => setMode("camera"));
  videoModeButton.addEventListener("click", () => setMode("video"));
  startButton.addEventListener("click", () => {
    if (state.mode === "camera") {
      void startCameraStream();
      return;
    }
    startVideoStream();
  });
  stopButton.addEventListener("click", disconnect);
  videoUploadInput.addEventListener("change", (event) => {
    const nextFile = event.target.files && event.target.files[0];
    if (!nextFile) {
      return;
    }

    uploadVideo(nextFile).catch((error) => {
      setStatus("error", error instanceof Error ? error.message : "Upload failed.");
    });
    event.target.value = "";
  });

  window.addEventListener("beforeunload", disconnect);

  setMode("camera");
  fetchSources();
})();

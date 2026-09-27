export function getWebcamErrorMessage(error: unknown) {
    if (error instanceof DOMException) {
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            return 'Camera access was denied. Allow permission in your browser and try again.';
        }
        if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
            return 'No webcam was detected on this device.';
        }
        if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
            return 'Your webcam is already in use by another application.';
        }
        if (error.name === 'OverconstrainedError') {
            return 'No compatible webcam configuration was found.';
        }
    }

    return 'Unable to access the webcam right now.';
}

export async function captureVideoFrameAsFile(
    video: HTMLVideoElement,
    filename = `webcam-capture-${Date.now()}.jpg`,
): Promise<File> {
    if (!video.videoWidth || !video.videoHeight) {
        throw new Error('The webcam is not ready yet. Try again in a moment.');
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const context = canvas.getContext('2d');
    if (!context) {
        throw new Error('Unable to process the captured frame.');
    }

    context.drawImage(video, 0, 0, canvas.width, canvas.height);

    const blob = await new Promise<Blob | null>((resolve) => {
        canvas.toBlob(resolve, 'image/jpeg', 0.92);
    });

    if (!blob) {
        throw new Error('Unable to capture the photo. Please try again.');
    }

    return new File([blob], filename, {
        type: 'image/jpeg',
        lastModified: Date.now(),
    });
}

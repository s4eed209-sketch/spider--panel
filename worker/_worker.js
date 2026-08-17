// TransformStream to count chunk bytes and enforce traffic caps
function createByteCounterStream(onByteChunk) {
  return new TransformStream({
    transform(chunk, controller) {
      if (chunk && chunk.byteLength) {
        onByteChunk(chunk.byteLength);
      }
      controller.enqueue(chunk);
    }
  });
}

// Inside the WebSocket / TCP relay handler:
async function handleVlessRelay(webSocket, tcpSocket, userContext, kvNamespace) {
  let totalSessionBytes = 0;
  const maxAllowedBytes = userContext.limit_bytes - userContext.used_bytes;

  const countAndEnforce = (bytes) => {
    totalSessionBytes += bytes;
    if (userContext.limit_bytes > 0 && totalSessionBytes > maxAllowedBytes) {
      try {
        webSocket.close(1008, "Traffic limit exceeded");
        tcpSocket.close();
      } catch (err) {
        // Safe close handling
      }
    }
  };

  const clientReadable = webSocket.readable.pipeThrough(createByteCounterStream(countAndEnforce));
  const serverReadable = tcpSocket.readable.pipeThrough(createByteCounterStream(countAndEnforce));

  await Promise.all([
    clientReadable.pipeTo(tcpSocket.writable),
    serverReadable.pipeTo(webSocket.writable)
  ]);

  // Sync remaining session usage back to KV periodically or on close
  if (totalSessionBytes > 0) {
    const updatedUsed = (userContext.used_bytes || 0) + totalSessionBytes;
    userContext.used_bytes = updatedUsed;
    await kvNamespace.put(`user:${userContext.uuid}`, JSON.stringify(userContext));
  }
}

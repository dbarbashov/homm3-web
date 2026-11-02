/* Updates are staged; an active game never switches worker/runtime versions. */
if ('serviceWorker' in navigator && isSecureContext) {
  navigator.serviceWorker.getRegistration('/').then(reg=>reg?.update()).catch(()=>{});
}

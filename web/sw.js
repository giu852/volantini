const C='v1',S=['./','index.html','manifest.json'];
self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(S))));
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);e.respondWith(u.pathname.endsWith('offerte.json')?fetch(e.request).then(r=>{const c=r.clone();caches.open(C).then(x=>x.put(e.request,c));return r}).catch(()=>caches.match(e.request)):caches.match(e.request).then(r=>r||fetch(e.request)))});

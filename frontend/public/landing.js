(function () {
  function startLanding() {
      var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
      var scenes = [].slice.call(document.querySelectorAll('.scene')), dots = [].slice.call(document.querySelectorAll('.dot'));
      var R = [[0, .12], [.12, .26], [.26, .40], [.40, .54], [.54, .80], [.80, .91], [.91, 1]];
      var DARK = { 4: 1 };
      var STOPS = [[0, '#03050D', '#0B1226'], [.19, '#050A1A', '#13214A'], [.33, '#0A2250', '#1F5FA8'], [.47, '#1F5FA8', '#5FB0DE'], [.61, '#6DB8E2', '#CFE8F6'], [.74, '#BFE3F5', '#B9E3AE'], [.80, '#8A7458', '#4A3523'], [.855, '#4A3523', '#2C2016'], [.91, '#2C2016', '#1B3A21'], [.95, '#16361C', '#0E2413'], [1, '#0B1C0F', '#183A1E']];
      var hex = function (h) { return [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16) }) };
      STOPS.forEach(function (s) { s[1] = hex(s[1]); s[2] = hex(s[2]) });
      var clamp = function (v) { return Math.max(0, Math.min(1, v)) };
      var ss = function (a, b, v) { var x = clamp((v - a) / (b - a)); return x * x * (3 - 2 * x) };
      var mix = function (a, b, t) { return a.map(function (v, i) { return Math.round(v + (b[i] - v) * t) }).join(',') };
      function bg(p) {
        var i = 0; while (i < STOPS.length - 2 && p > STOPS[i + 1][0]) i++;
        var a = STOPS[i], b = STOPS[i + 1], t = clamp((p - a[0]) / (b[0] - a[0]));
        document.getElementById('bg').style.background = 'linear-gradient(180deg,rgb(' + mix(a[1], b[1], t) + '),rgb(' + mix(a[2], b[2], t) + '))';
      }
      var target = 0, cur = 0, K = reduced ? 1 : .08;
      var maxS = function () { return document.documentElement.scrollHeight - innerHeight };
      function onS() { var m = maxS(); target = m > 0 ? scrollY / m : 0 }
      addEventListener('scroll', onS, { passive: true }); onS();

      var lenis = (typeof Lenis !== 'undefined' && !reduced) ? new Lenis({
        duration: 1.8,
        easing: function (t) { return Math.min(1, 1.001 - Math.pow(2, -10 * t)) },
        smoothWheel: true,
        wheelMultiplier: 0.45,
        touchMultiplier: 1.0
      }) : null;

      dots.forEach(function (d, i) {
        d.addEventListener('click', function () {
          var dest = (R[i][0] + (R[i][1] - R[i][0]) * .3) * maxS();
          if (lenis) lenis.scrollTo(dest, { duration: 1.4 });
          else scrollTo({ top: dest, behavior: 'smooth' });
        });
      });
      var topB = document.getElementById('top');
      topB.addEventListener('click', function () {
        if (lenis) lenis.scrollTo(0, { duration: 1.4 });
        else scrollTo({ top: 0, behavior: 'smooth' });
      });
      var g = function (id) { return document.getElementById(id) };
      var pars = scenes.map(function (s) { return [].slice.call(s.querySelectorAll('.par')) });
      var plane = g('plane'), planeW = 220;
      var cpA = g('cpA'), cpB = g('cpB'), rot = g('rot'), frame = g('frame'), stDot = g('stDot'), stTxt = g('stTxt'), lastY = -1;
      var plots = [0, 1, 2, 3].map(function (k) { return g('pl' + k) });
      var PX = [[0, 0], [117.4, 0], [117.4, 117.4], [0, 117.4]];
      var YR = [['Year 1 · Drought test', '#DE7B3C'], ['Year 2 · Heat test', '#C8433B'], ['Year 3 · Frost test', '#4FA3D1'], ['Year 4 · All clear', '#4E9A4A']];
      scenes.forEach(function (s, i) { if (DARK[i]) s.classList.add('dk') });
      var hl = g('hl'), hv = g('hv'), lastH = '', hudEl = document.querySelector('.hud');
      function hud(p) {
        var l, v;
        if (p < .66) { var a = 36000 * Math.pow(1 - p / .66, 3); l = 'Altitude'; v = a >= 100 ? Math.round(a).toLocaleString('en-US') + ' km' : a >= 1 ? a.toFixed(1) + ' km' : Math.round(a * 1000) + ' m' }
        else if (p < .8) { l = 'Altitude'; v = '0 m' }
        else { l = 'Depth'; v = Math.round(clamp((p - .8) / .1) * 150) + ' cm' }
        hudEl.style.opacity = 1 - ss(.89, .94, p);
        if (l && l + v !== lastH) { lastH = l + v; hl.textContent = l; hv.textContent = v }
      }

      /* Three.js 3D Earth Setup */
      var earthCanvas = g('earth-canvas');
      var earthMesh = null, earthGroup = null, earthRenderer = null, earthCamera = null, earthScene = null;
      var initialY = -Math.PI * 0.45;

      if (typeof THREE !== 'undefined' && earthCanvas) {
        earthScene = new THREE.Scene();
        earthCamera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
        earthCamera.position.z = 2.65;

        earthRenderer = new THREE.WebGLRenderer({ canvas: earthCanvas, alpha: true, antialias: true, powerPreference: 'high-performance' });
        earthRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        earthRenderer.setSize(960, 960, false);

        var ambientLight = new THREE.AmbientLight(0xffffff, 1.05);
        earthScene.add(ambientLight);
        var dirLight = new THREE.DirectionalLight(0xffffff, 0.45);
        dirLight.position.set(-2, 1.5, 3);
        earthScene.add(dirLight);

        var texLoader = new THREE.TextureLoader();
        texLoader.load('/earth_map_4k.jpg', function (tex) {
          if (THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
          tex.generateMipmaps = true;
          tex.minFilter = THREE.LinearMipmapLinearFilter;
          tex.magFilter = THREE.LinearFilter;
          var maxAniso = earthRenderer.capabilities.getMaxAnisotropy();
          if (maxAniso > 1) tex.anisotropy = maxAniso;

          var geom = new THREE.SphereGeometry(1, 128, 96);
          var mat = new THREE.MeshLambertMaterial({ map: tex });
          earthMesh = new THREE.Mesh(geom, mat);
          earthMesh.rotation.y = initialY;

          earthGroup = new THREE.Group();
          earthGroup.rotation.z = THREE.MathUtils ? THREE.MathUtils.degToRad(23.4) : (23.4 * Math.PI / 180);
          earthGroup.add(earthMesh);
          earthScene.add(earthGroup);

          earthRenderer.render(earthScene, earthCamera);
        });
      }

      function update(p) {
        var best = 0, mx = -1;
        scenes.forEach(function (sc, i) {
          var s = R[i][0], e = R[i][1], lp = clamp((p - s) / (e - s)), op;
          if (i === 0) op = 1 - ss(.09, .13, p);
          else if (i === scenes.length - 1) op = ss(s - .02, s + .03, p);
          else op = Math.min(ss(s - .02, s + .03, p), 1 - ss(e - .03, e + .02, p));
          sc.style.opacity = op; sc.classList.toggle('on', op > .005);
          if (op > mx) { mx = op; best = i }
          pars[i].forEach(function (el) { el.style.transform = 'translate3d(0,' + ((.5 - lp) * el.getAttribute('data-s')) + 'px,0)' });
          var c = 'translate(-50%,-50%) ';
          if (i === 0) sc.querySelector('.copy').style.transform = 'translate3d(0,' + (-lp * 70) + 'px,0)';
          else if (i === 1) {
            g('earth').style.transform = c + 'scale(' + (.4 + 1.1 * ss(0, 1, lp)) + ')';
            if (earthMesh && earthRenderer && op > 0.005) {
              earthMesh.rotation.y = initialY + (reduced ? 0 : lp * 2.4);
              earthRenderer.render(earthScene, earthCamera);
            }
          }
          else if (i === 2) { g('limb').style.transform = 'translate3d(0,' + ((1 - ss(0, .5, lp)) * 160) + 'px,0)'; g('cols').style.transform = 'translate3d(0,' + ((1 - ss(.1, .5, lp)) * 40) + 'px,0)' }
          else if (i === 3) {
            var pr = clamp((lp - .1) / .8);
            var px = -planeW + (innerWidth + planeW * 2.4) * pr;
            var py = (pr - .5) * 90 + Math.sin(pr * 6.283) * 8;
            plane.style.transform = 'translate3d(' + px + 'px,' + py + 'px,0) rotate(' + (2.5 + Math.sin(pr * 6.283) * 1.2) + 'deg)';
          }
          else if (i === 4) {
            var oa = 1 - ss(.38, .46, lp), ob = ss(.44, .52, lp);
            cpA.style.opacity = oa; cpA.style.transform = 'translate3d(0,' + ((1 - oa) * -14) + 'px,0)';
            cpB.style.opacity = ob; cpB.style.transform = 'translate3d(0,' + ((1 - ob) * 14) + 'px,0)';
            rot.style.transform = c + 'scale(' + (.55 + .45 * ss(0, .22, lp)) + ')';
            var rt = 3 * clamp((lp - .2) / .62), sn = Math.min(2, Math.floor(rt)), fr = ss(.2, .8, rt - sn);
            for (var k = 0; k < 4; k++) {
              var pa = PX[(k + sn) % 4], pb = PX[(k + sn + 1) % 4];
              plots[k].style.transform = 'translate(' + (pa[0] + (pb[0] - pa[0]) * fr) + '%,' + (pa[1] + (pb[1] - pa[1]) * fr) + '%)';
            }
            var yi = Math.min(3, Math.floor(rt + .5));
            if (yi !== lastY) { lastY = yi; stTxt.textContent = YR[yi][0]; stDot.style.background = YR[yi][1]; frame.style.borderColor = YR[yi][1] }
          }
          else if (i === 5) g('soil').style.transform = c + 'scale(' + (.75 + .25 * ss(0, .6, lp)) + ')';
          else if (i === 6) g('end').style.transform = 'translate3d(0,' + ((1 - ss(0, .6, lp)) * 30) + 'px,0)';
        });
        dots.forEach(function (d, i) { d.classList.toggle('a', i === best) });
        document.documentElement.style.setProperty('--cfg', DARK[best] ? '#1B3A21' : '#E8F0EA');
        topB.classList.toggle('v', p > .3);
        bg(p); hud(p);
      }
      function tick(time) {
        if (lenis) {
          lenis.raf(time);
          var m = maxS();
          cur = m > 0 ? clamp(scrollY / m) : 0;
        } else {
          cur += (target - cur) * K;
        }
        update(cur);
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);

      /* Stars up high, pollen near the ground */
      var cv = g('fx'), ctx = cv.getContext('2d'), P = [];
      var POL = ['78,154,74', '47,94,51', '125,90,60', '217,178,58'], LT = ['123,201,111', '185,227,174', '78,154,74', '220,199,174'];
      function size() {
        planeW = plane.offsetWidth || 220;
        var d = Math.min(devicePixelRatio || 1, 2); cv.width = innerWidth * d; cv.height = innerHeight * d; ctx.setTransform(d, 0, 0, d, 0, 0);
        P = []; var n = innerWidth < 768 ? 110 : 240;
        for (var i = 0; i < n; i++)P.push({ x: Math.random() * innerWidth, y: Math.random() * innerHeight, r: Math.random() * 1.7 + .5, z: Math.random() * .7 + .2, ph: Math.random() * 6.28, ts: Math.random() * .003 + .001, a: Math.random() * .5 + .35, c: POL[i % 4], i: i % 4, star: i % 3 !== 0 });
      }
      function draw(t) {
        ctx.clearRect(0, 0, innerWidth, innerHeight);
        var fs = 1 - ss(.3, .5, cur), fp = ss(.7, .82, cur), H = innerHeight;
        for (var i = 0; i < P.length; i++) {
          var s = P[i], k = s.star ? fs : fp; if (k < .01) continue;
          var y = (((s.y - scrollY * s.z * .25) % H) + H) % H, x = s.x + (s.star || reduced ? 0 : Math.sin(t * .0005 + s.ph) * 12);
          ctx.fillStyle = 'rgba(' + (s.star ? '255,255,255' : (cur > .78 ? LT[s.i] : s.c)) + ',' + (s.a * k * (.5 + .5 * Math.sin(t * s.ts + s.ph))) + ')';
          ctx.beginPath(); ctx.arc(x, y, s.r, 0, 6.283); ctx.fill();
        }
        requestAnimationFrame(draw);
      }
      addEventListener('resize', size); size(); requestAnimationFrame(draw);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startLanding);
  } else {
    startLanding();
  }
})();

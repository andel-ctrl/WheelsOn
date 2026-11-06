/* Comportamiento global de WheelsOn: notificaciones, brillo del vidrio, fondo y login. */

/* Panel de notificaciones. Los avisos vienen del grafo; lo único que se guarda aquí
   es cuáles ya se vieron, y solo en este navegador. */
function panelAvisos(uid) {
    var clave = 'wheelson-avisos-vistos:' + uid;
    function leerVistos() {
        try { return JSON.parse(localStorage.getItem(clave)) || []; } catch (e) { return []; }
    }
    return {
        abierto: false,
        vistos: [],
        ids: [],
        init: function () {
            this.vistos = leerVistos();
            this.ids = Array.prototype.map.call(this.$el.querySelectorAll('[data-aviso]'), function (nodo) {
                return nodo.getAttribute('data-aviso');
            });
        },
        esNuevo: function (id) { return this.vistos.indexOf(id) === -1; },
        get cantidadNuevos() {
            var vistos = this.vistos;
            return this.ids.filter(function (id) { return vistos.indexOf(id) === -1; }).length;
        },
        alternar: function () { this.abierto ? this.cerrar() : (this.abierto = true); },
        cerrar: function () {
            if (!this.abierto) { return; }
            this.abierto = false;
            this.vistos = this.ids.slice();
            try { localStorage.setItem(clave, JSON.stringify(this.vistos)); } catch (e) { /* sin almacenamiento, nada que recordar */ }
        }
    };
}

/* Brillo del vidrio líquido: sigue al puntero sobre la tarjeta que esté debajo. */
(function () {
    if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) { return; }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { return; }
    var pendiente = null, evento = null;
    function aplicar() {
        pendiente = null;
        var vidrio = evento.target.closest && evento.target.closest('.ws-hito, .ws-panel, .ws-compositor');
        if (!vidrio) { return; }
        var caja = vidrio.getBoundingClientRect();
        vidrio.style.setProperty('--x', (evento.clientX - caja.left) + 'px');
        vidrio.style.setProperty('--y', (evento.clientY - caja.top) + 'px');
    }
    document.addEventListener('pointermove', function (e) {
        evento = e;
        if (pendiente === null) { pendiente = requestAnimationFrame(aplicar); }
    }, { passive: true });
})();

/* Fondo: las formas se mueven solas con CSS; aquí se suma un desplazamiento suave hacia el puntero. */
(function () {
    function iniciar() {
        var fondo = document.querySelector('[data-ws-fondo]');
        if (!fondo || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { return; }
        if (!window.matchMedia('(hover: hover) and (pointer: fine)').matches) { return; }
        var x = 0, y = 0, metaX = 0, metaY = 0, marco = null;
        function paso() {
            x += (metaX - x) * 0.06;
            y += (metaY - y) * 0.06;
            fondo.style.setProperty('--px', x.toFixed(3));
            fondo.style.setProperty('--py', y.toFixed(3));
            marco = Math.abs(metaX - x) + Math.abs(metaY - y) > 0.002 ? requestAnimationFrame(paso) : null;
        }
        document.addEventListener('pointermove', function (e) {
            metaX = e.clientX / window.innerWidth - 0.5;
            metaY = e.clientY / window.innerHeight - 0.5;
            if (marco === null) { marco = requestAnimationFrame(paso); }
        }, { passive: true });
    }
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', iniciar); } else { iniciar(); }
})();

/* Login: el borde entre la foto y el formulario es una ola. Cada tecla le manda una onda
   y hace rodar la rueda del logo. Con movimiento reducido, la ola se dibuja una vez y queda quieta. */
(function () {
    function iniciar() {
        var acceso = document.querySelector('[data-ws-acceso]');
        if (!acceso) { return; }

        acceso.querySelectorAll('[data-ver-clave]').forEach(function (boton) {
            boton.addEventListener('click', function () {
                var campo = document.getElementById(boton.getAttribute('data-ver-clave'));
                var visible = campo.type === 'password';
                campo.type = visible ? 'text' : 'password';
                boton.setAttribute('aria-pressed', String(visible));
                boton.setAttribute('aria-label', visible ? 'Ocultar contraseña' : 'Mostrar contraseña');
            });
        });

        var foto = acceso.querySelector('[data-ws-ola-foto]');
        var linea = acceso.querySelector('[data-ws-ola-linea]');
        var eco = acceso.querySelector('[data-ws-ola-eco]');
        var rueda = acceso.querySelector('.ws-logo__rueda');
        var quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        var ancho = 0, alto = 0, angosto = false, ondas = [], giro = 0, marco = null, ultimo = 0;
        var fuerza = 0, inicioOla = null; /* la ola nace recta y gana movimiento poco a poco */

        function medir() {
            ancho = acceso.clientWidth;
            alto = acceso.clientHeight;
            angosto = ancho < 900;
        }

        /* Cuánto se aparta la ola de su posición en el punto `s` del borde */
        function desvio(s, t) {
            var d = (Math.sin(s * 0.0052 + t * 0.55) * 17 + Math.sin(s * 0.0125 - t * 0.38) * 8) * fuerza;
            var onda = 0;
            for (var i = 0; i < ondas.length; i++) {
                var o = ondas[i], edad = t - o.t;
                var arriba = s - o.s + edad * 520, abajo = s - o.s - edad * 520;
                /* La onda crece poco a poco: no nace de golpe */
                onda += 8 * (1 - Math.exp(-edad * 7)) * (Math.exp(-arriba * arriba / 14000) + Math.exp(-abajo * abajo / 14000)) * Math.exp(-edad * 1.3);
            }
            /* Escribir rápido no debe deformar el borde: las ondas se suman, pero con un tope suave */
            return d + 20 * Math.tanh(onda / 20);
        }

        function dibujar(t) {
            var largo = angosto ? ancho : alto;
            var base = angosto ? 300 : ancho * 0.58;
            var puntos = [], ecos = [];
            for (var s = 0; s <= largo + 16; s += 16) {
                var d = desvio(s, t);
                if (angosto) {
                    puntos.push(s + ' ' + (base + d * 0.6).toFixed(1));
                    ecos.push(s + ' ' + (base + 12 + d * 0.9).toFixed(1));
                } else {
                    puntos.push((base + d).toFixed(1) + ' ' + s);
                    ecos.push((base + 16 + d * 1.35).toFixed(1) + ' ' + s);
                }
            }
            var trazo = 'M' + puntos.join('L');
            foto.style.clipPath = angosto
                ? "path('M0 0L" + (ancho + 16) + ' 0L' + puntos.slice().reverse().join('L') + "Z')"
                : "path('M0 0L" + puntos.join('L') + 'L0 ' + (alto + 16) + "Z')";
            linea.setAttribute('d', trazo);
            eco.setAttribute('d', 'M' + ecos.join('L'));
        }

        function bucle(ahora) {
            marco = requestAnimationFrame(bucle);
            if (ahora - ultimo < 33) { return; }
            ultimo = ahora;
            var t = ahora / 1000;
            if (inicioOla === null) { inicioOla = t; }
            var avance = Math.min(1, (t - inicioOla) / 1.6);
            fuerza = avance * avance * (3 - 2 * avance);
            ondas = ondas.filter(function (o) { return t - o.t < 3.5; });
            dibujar(t);
        }

        function rodar(grados) {
            if (!rueda) { return; }
            giro += grados;
            rueda.style.transform = 'rotate(' + giro + 'deg)';
        }

        window.addEventListener('resize', function () { medir(); dibujar(performance.now() / 1000); });
        medir();
        if (quieto) { fuerza = 1; }
        dibujar(performance.now() / 1000);
        if (quieto) { return; }

        document.addEventListener('visibilitychange', function () {
            if (document.hidden) { cancelAnimationFrame(marco); marco = null; }
            else if (marco === null && inicioOla !== null) { marco = requestAnimationFrame(bucle); }
        });

        /* Espera a que la página termine de cargar y la foto esté lista, para no arrancar a saltos */
        function arrancar() {
            var imagen = foto.querySelector('img');
            var lista = imagen && imagen.decode ? imagen.decode().catch(function () {}) : Promise.resolve();
            lista.then(function () { if (marco === null) { marco = requestAnimationFrame(bucle); } });
        }
        if (document.readyState === 'complete') { arrancar(); } else { window.addEventListener('load', arrancar); }

        acceso.addEventListener('input', function (e) {
            /* Solo lo que la persona teclea: el relleno automático del navegador no trae inputType */
            if (!e.target.matches('input') || !e.inputType) { return; }
            var caja = e.target.getBoundingClientRect(), raiz = acceso.getBoundingClientRect();
            var s = angosto ? caja.left - raiz.left + caja.width / 2 : caja.top - raiz.top + caja.height / 2;
            if (ondas.length < 6) { ondas.push({ s: s, t: performance.now() / 1000 }); }
            rodar(48);
        });
        var formulario = acceso.querySelector('form');
        if (formulario) { formulario.addEventListener('submit', function () { rodar(360); }); }
    }
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', iniciar); } else { iniciar(); }
})();

/* Ver más: pide solo los elementos siguientes y los suma a la lista, sin recargar. Si algo
   falla, el botón sigue siendo un enlace normal y la página llega completa. */
(function () {
    document.addEventListener('click', function (evento) {
        var enlace = evento.target.closest ? evento.target.closest('[data-ws-ver-mas]') : null;
        if (!enlace || evento.metaKey || evento.ctrlKey || evento.shiftKey) { return; }
        var lista = document.getElementById(enlace.getAttribute('data-ws-ver-mas'));
        if (!lista) { return; }
        evento.preventDefault();
        if (enlace.classList.contains('is-cargando')) { return; }
        enlace.classList.add('is-cargando');
        enlace.setAttribute('aria-busy', 'true');

        var url = new URL(enlace.href);
        url.searchParams.set('fragmento', '1');
        fetch(url.toString(), { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
            .then(function (respuesta) {
                if (!respuesta.ok || respuesta.redirected) { throw new Error('ver mas'); }
                return respuesta.text();
            })
            .then(function (html) {
                var plantilla = document.createElement('template');
                plantilla.innerHTML = html;
                var siguiente = plantilla.content.querySelector('.ws-ver-mas');
                var contenedorViejo = enlace.closest('.ws-ver-mas');
                if (siguiente) { siguiente.remove(); }
                var primero = plantilla.content.firstElementChild;
                lista.appendChild(plantilla.content);
                if (siguiente) { contenedorViejo.replaceWith(siguiente); } else { contenedorViejo.remove(); }
                history.replaceState(null, '', enlace.href);
                var foco = primero && primero.querySelector('h2 a, h3 a, a[href]:not([tabindex="-1"]), button');
                if (!foco && primero) { primero.setAttribute('tabindex', '-1'); foco = primero; }
                if (foco) { foco.focus({ preventScroll: true }); }
            })
            .catch(function () { window.location.href = enlace.href; });
    });
})();

/* Tema claro u oscuro. Se guarda en este navegador. Los gráficos y el grafo se dibujan en
   un lienzo con sus colores ya calculados, así que esas páginas se recargan al cambiar,
   después de que termine la animación del interruptor. */
(function () {
    var CLAVE = 'wheelson-tema';
    var raiz = document.documentElement;
    function oscuro() { return raiz.getAttribute('data-tema') === 'oscuro'; }
    function marcar() {
        document.querySelectorAll('[data-ws-tema-interruptor]').forEach(function (boton) {
            boton.setAttribute('aria-checked', oscuro() ? 'true' : 'false');
            boton.setAttribute('title', oscuro() ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro');
        });
        var color = document.querySelector('meta[name="theme-color"]');
        if (color) { color.setAttribute('content', oscuro() ? '#07090C' : '#FAF7F6'); }
    }
    function aplicar(tema) {
        if (tema === 'oscuro') { raiz.setAttribute('data-tema', 'oscuro'); } else { raiz.removeAttribute('data-tema'); }
        marcar();
    }
    document.addEventListener('click', function (evento) {
        var boton = evento.target.closest ? evento.target.closest('[data-ws-tema-interruptor]') : null;
        if (!boton) { return; }
        var tema = oscuro() ? 'claro' : 'oscuro';
        aplicar(tema);
        try { localStorage.setItem(CLAVE, tema); } catch (e) {}
        if (document.querySelector('canvas, #user-constellation-network, #vis-graph-canvas')) {
            setTimeout(function () { window.location.reload(); }, 420);
        }
    }, true); // En captura: el menú móvil detiene los clics antes de que lleguen al documento
    if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', marcar); } else { marcar(); }
    window.addEventListener('storage', function (evento) {
        if (evento.key === CLAVE) { aplicar(evento.newValue); }
    });
})();

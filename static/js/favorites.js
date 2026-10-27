(function () {
    if (window.favoritesInstalled) return;
    window.favoritesInstalled = true;

    // Tidak mengubah hati secara optimistis: status hanya berubah setelah server berhasil.
    // Jika satu listing muncul di beberapa tempat, semua kontrol mengikuti event server.
    document.body.addEventListener('favoriteChanged', function (event) {
        const listingId = String(event.detail.listingId);
        const saved = event.detail.saved === true;
        document.querySelectorAll('.favorite-control').forEach(function (control) {
            if (control.dataset.listingId !== listingId) return;
            const form = control.querySelector('form[data-favorite-action]');
            if (!form) return;
            const action = saved ? form.dataset.removeUrl : form.dataset.addUrl;
            form.action = action;
            form.setAttribute('hx-post', action);
            const button = form.querySelector('button');
            button.setAttribute('aria-pressed', String(saved));
            button.setAttribute('aria-label', saved ? 'Hapus dari favorit' : 'Simpan ke favorit');
            button.querySelector('svg').setAttribute('fill', saved ? 'currentColor' : 'none');
            // HTMX menyimpan handler URL; proses ulang jika atribut aksi berubah.
            if (window.htmx) htmx.process(form);
        });
    });

    function showFailure(event) {
        const form = event.detail.elt && event.detail.elt.closest('[data-favorite-action]');
        if (!form) return;
        let error = form.querySelector('[data-favorite-error]');
        if (!error) {
            error = document.createElement('p');
            error.dataset.favoriteError = '';
            error.className = 'text-sm text-error mt-3';
            error.setAttribute('role', 'alert');
            form.appendChild(error);
        }
        error.textContent = 'Permintaan belum dapat dikonfirmasi. Coba lagi atau muat ulang halaman untuk memastikan status.';
    }

    ['htmx:responseError', 'htmx:sendError', 'htmx:timeout', 'htmx:swapError'].forEach(function (name) {
        document.body.addEventListener(name, showFailure);
    });
    document.body.addEventListener('htmx:beforeRequest', function (event) {
        const form = event.detail.elt && event.detail.elt.closest('[data-favorite-action]');
        const error = form && form.querySelector('[data-favorite-error]');
        if (error) error.remove();
    });
})();

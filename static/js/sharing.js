document.addEventListener('DOMContentLoaded', () => {
  const modalElement = document.getElementById('shareModal');
  const content = document.getElementById('shareModalContent');
  let searchTimer;

  async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const type = response.headers.get('content-type') || '';
    if (!type.includes('application/json')) throw new Error('The sharing request could not be completed.');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The sharing request failed.');
    return data;
  }

  async function openShare(url) {
    if (!modalElement || !content) return;
    content.innerHTML = '<div class="modal-body modal-loading"><span class="spinner-border"></span><p>Loading sharing settings…</p></div>';
    bootstrap.Modal.getOrCreateInstance(modalElement).show();
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('Unable to load sharing settings.');
      content.innerHTML = await response.text();
      wireDialog(url);
    } catch (error) {
      content.innerHTML = `<div class="modal-body delete-copy"><span><i class="bi bi-exclamation-circle"></i></span><h4>Sharing unavailable</h4><p>${escapeText(error.message)}</p><button class="btn btn-light" data-bs-dismiss="modal">Close</button></div>`;
    }
  }

  document.addEventListener('click', event => {
    const trigger = event.target.closest('.share-trigger');
    if (trigger) {
      event.preventDefault();
      openShare(trigger.dataset.url);
    }
  });

  function wireDialog(dialogUrl) {
    const search = document.getElementById('shareUserSearch');
    const results = document.getElementById('shareUserResults');
    const userId = document.getElementById('shareUserId');

    search?.addEventListener('input', () => {
      clearTimeout(searchTimer);
      userId.value = '';
      searchTimer = setTimeout(async () => {
        if (search.value.trim().length < 2) { results.innerHTML = ''; return; }
        try {
          const data = await requestJson(`/sharing/users/?q=${encodeURIComponent(search.value)}`);
          results.innerHTML = data.users.map(user => `<button type="button" data-id="${user.id}" data-name="${escapeText(user.name)}"><span class="avatar">${escapeText(user.initials)}</span><span><b>${escapeText(user.name)}</b><small>${escapeText(user.email || '')}</small></span></button>`).join('') || '<small>No users found</small>';
          results.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
            userId.value = button.dataset.id;
            search.value = button.dataset.name;
            results.innerHTML = '';
          }));
        } catch (error) { results.innerHTML = `<small class="text-danger">${escapeText(error.message)}</small>`; }
      }, 320);
    });

    document.getElementById('addShareForm')?.addEventListener('submit', async event => {
      event.preventDefault();
      if (!userId.value) { toast('Choose a person first', true); return; }
      try {
        const data = await requestJson(event.target.action, {method: 'POST', body: new FormData(event.target), headers: {'X-CSRFToken': decodeURIComponent(cookie('csrftoken'))}});
        toast(data.message);
        setTimeout(() => openShare(dialogUrl), 250);
      } catch (error) { toast(error.message, true); }
    });

    const toggle = document.getElementById('publicAccessToggle');
    const settings = document.getElementById('linkSettingsForm');
    toggle?.addEventListener('change', () => {
      settings.classList.toggle('d-none', !toggle.checked);
      if (toggle.checked && !document.getElementById('publicLinkValue')) settings.requestSubmit();
    });
    document.getElementById('requireLinkPassword')?.addEventListener('change', event => document.getElementById('linkPassword').classList.toggle('d-none', !event.target.checked));
    settings?.addEventListener('submit', async event => {
      event.preventDefault();
      try {
        const data = await requestJson(event.target.action, {method: 'POST', body: new FormData(event.target), headers: {'X-CSRFToken': decodeURIComponent(cookie('csrftoken'))}});
        toast(data.message);
        setTimeout(() => openShare(dialogUrl), 250);
      } catch (error) { toast(error.message, true); }
    });
    document.getElementById('copyShareLink')?.addEventListener('click', async () => {
      const copied = await copyText(document.getElementById('publicLinkValue').value);
      toast(copied ? 'Link copied' : 'Unable to copy the link. Select and copy it manually.', !copied);
    });
  }

  function escapeText(value) {
    const element = document.createElement('div');
    element.textContent = value;
    return element.innerHTML;
  }
});

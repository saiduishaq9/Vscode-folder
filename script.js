(function () {
  const setYear = () => {
    const yearNode = document.getElementById('year');
    if (yearNode) {
      yearNode.textContent = new Date().getFullYear();
    }
  };

  const handleFormStatus = (statusNode, message, isError = false) => {
    if (!statusNode) return;
    statusNode.textContent = message;
    statusNode.style.color = isError ? '#b42318' : '#226d53';
  };

  const parseResponse = async (response) => {
    const content = await response.json().catch(() => ({}));
    return {
      ok: response.ok,
      data: content,
      status: response.status
    };
  };

  const updateDecision = async (applicationId, decision) => {
    const response = await fetch(`/api/admin/applications/${applicationId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision })
    });
    const result = await parseResponse(response);

    if (!result.ok || !result.data.success) {
      throw new Error(result.data.message || 'Could not update application status.');
    }

    await renderAdminPanel();
    return result.data.message;
  };

  const renderAdminPanel = async () => {
    const tableBody = document.getElementById('adminTableBody');
    const statTotal = document.getElementById('statTotal');
    const statPending = document.getElementById('statPending');
    const statAccepted = document.getElementById('statAccepted');

    if (!tableBody) return;

    try {
      const response = await fetch('/api/admin/applications');
      const applications = await response.json();

      if (!Array.isArray(applications)) {
        throw new Error('Unable to load applications.');
      }

      if (statTotal) statTotal.textContent = String(applications.length);
      if (statPending) statPending.textContent = String(applications.filter((app) => String(app.decision || '').toLowerCase().includes('pending')).length);
      if (statAccepted) statAccepted.textContent = String(applications.filter((app) => String(app.decision || '').toLowerCase().includes('accepted')).length);

      if (!applications.length) {
        tableBody.innerHTML = '<tr><td colspan="7">No applications submitted yet.</td></tr>';
        return;
      }

      tableBody.innerHTML = applications.map((app) => {
        const status = app.decision || app.status || 'Pending';
        const className = String(status).toLowerCase().includes('accepted') ? 'accepted' : (String(status).toLowerCase().includes('rejected') ? 'rejected' : 'pending');

        return `
          <tr>
            <td>${app.applicantId || '—'}</td>
            <td>${app.fullName || '—'}</td>
            <td>${app.classLevel || '—'}</td>
            <td>${app.email || '—'}</td>
            <td>${app.phone || '—'}</td>
            <td><span class="status-pill ${className}">${status}</span></td>
            <td>
              <div class="action-row">
                <button class="mini-btn success" data-action="accept" data-id="${app.id}">Accept</button>
                <button class="mini-btn danger" data-action="reject" data-id="${app.id}">Reject</button>
              </div>
            </td>
          </tr>
        `;
      }).join('');

      tableBody.querySelectorAll('button[data-action]').forEach((button) => {
        button.addEventListener('click', async () => {
          const applicationId = button.dataset.id;
          const action = button.dataset.action;
          const decision = action === 'accept' ? 'Accepted' : 'Rejected';

          try {
            const message = await updateDecision(applicationId, decision);
            window.alert(message);
          } catch (error) {
            window.alert(error.message || 'Failed to update the application status.');
          }
        });
      });
    } catch (error) {
      tableBody.innerHTML = '<tr><td colspan="7">Unable to load applications.</td></tr>';
    }
  };

  const resultForm = document.getElementById('resultForm');
  const loginForm = document.getElementById('loginForm');
  const applicationForm = document.getElementById('applicationForm');

  if (resultForm) {
    resultForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const statusNode = document.getElementById('resultStatus');
      const applicantId = (new FormData(resultForm).get('applicantId') || '').toString().trim();

      try {
        const response = await fetch('/api/results', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ applicantId })
        });
        const result = await parseResponse(response);

        if (!result.ok || !result.data.success) {
          throw new Error(result.data.message || 'Unable to fetch result.');
        }

        handleFormStatus(statusNode, result.data.message);
      } catch (error) {
        handleFormStatus(statusNode, error.message || 'Unable to check result.', true);
      } finally {
        resultForm.reset();
      }
    });
  }

  if (loginForm) {
    loginForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const statusNode = document.getElementById('loginStatus');
      const formData = Object.fromEntries(new FormData(loginForm).entries());

      try {
        const response = await fetch('/api/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
        const result = await parseResponse(response);

        if (!result.ok || !result.data.success) {
          throw new Error(result.data.message || 'Login failed.');
        }

        handleFormStatus(statusNode, result.data.message);

        if (result.data.redirect) {
          window.location.href = result.data.redirect;
        }
      } catch (error) {
        handleFormStatus(statusNode, error.message || 'Login failed.', true);
      } finally {
        loginForm.reset();
      }
    });
  }

  if (applicationForm) {
    applicationForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const statusNode = document.getElementById('applicationStatus');
      const formData = Object.fromEntries(new FormData(applicationForm).entries());

      try {
        const response = await fetch('/api/applications', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
        const result = await parseResponse(response);

        if (!result.ok || !result.data.success) {
          throw new Error(result.data.message || 'Application submission failed.');
        }

        const applicantId = result.data.applicantId || 'BHR-UNKNOWN';
        handleFormStatus(statusNode, `${result.data.message} Applicant ID: ${applicantId}.`);
      } catch (error) {
        handleFormStatus(statusNode, error.message || 'Application submission failed.', true);
      } finally {
        applicationForm.reset();
      }
    });
  }

  renderAdminPanel();
  setYear();
})();

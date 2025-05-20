document.body.innerHTML = '<div id="app"></div>';

const appModule = require('./app');
const { handleChatSubmit, chatMessages, renderMenu } = appModule;

// Mock fetch and DOM
beforeEach(() => {
  global.fetch = jest.fn();
  chatMessages.length = 0;
  appModule.pendingRemoval = null;
  document.body.innerHTML = '<div id="app"></div>';
  // Reset pendingConfirmation and other globals
  if (typeof window !== 'undefined') window.pendingConfirmation = null;
  if (typeof globalThis !== 'undefined') globalThis.pendingConfirmation = null;
});

describe('Destructive Action Confirmation (confirmation_id protocol)', () => {
  beforeEach(() => {
    chatMessages.length = 0;
    appModule.pendingConfirmation = null;
  });

  it('should show confirmation prompt when backend returns confirmation_id', async () => {
    // Mock fetch for /chat/ to return confirmation-required
    global.fetch = jest.fn((url) => {
      if (url === '/chat/') {
        return Promise.resolve({
          json: () => Promise.resolve({
            reply: {
              stage: 'confirming_removal',
              confirmation_id: 'abc123',
              message: 'Are you sure you want to delete meal 1?'
            },
            stage: 'confirming_removal'
          })
        });
      }
      return Promise.resolve({ json: () => Promise.resolve({}) });
    });
    document.body.innerHTML = '<div id="app"></div>';
    const input = document.createElement('input');
    input.id = 'chatInput';
    input.value = 'delete meal 1';
    document.body.appendChild(input);
    await handleChatSubmit({ preventDefault: () => {} });
    await new Promise(r => setTimeout(r, 10));
    expect(appModule.pendingConfirmation).not.toBeNull();
    expect(chatMessages[chatMessages.length-1].content).toMatch(/are you sure/i);
  });

  it('should send /confirm_action when user confirms', async () => {
    appModule.pendingConfirmation = { confirmation_id: 'abc123', message: 'Are you sure?' };
    global.fetch = jest.fn((url) => {
      if (url === '/confirm_action') {
        return Promise.resolve({
          json: () => Promise.resolve({ stage: 'created', message: 'Meal deleted.' })
        });
      }
      return Promise.resolve({ json: () => Promise.resolve({}) });
    });
    document.body.innerHTML = '<div id="app"></div>';
    const input = document.createElement('input');
    input.id = 'chatInput';
    input.value = 'yes';
    document.body.appendChild(input);
    await handleChatSubmit({ preventDefault: () => {} });
    await new Promise(r => setTimeout(r, 10));
    expect(global.fetch).toHaveBeenCalledWith('/confirm_action', expect.anything());
    expect(chatMessages[chatMessages.length-1].content).toMatch(/deleted/i);
    expect(appModule.pendingConfirmation).toBeNull();
  });

  it('should not send /confirm_action if user cancels', async () => {
    appModule.pendingConfirmation = { confirmation_id: 'abc123', message: 'Are you sure?' };
    global.fetch = jest.fn();
    document.body.innerHTML = '<div id="app"></div>';
    const input = document.createElement('input');
    input.id = 'chatInput';
    input.value = 'no';
    document.body.appendChild(input);
    await handleChatSubmit({ preventDefault: () => {} });
    await new Promise(r => setTimeout(r, 10));
    expect(global.fetch).not.toHaveBeenCalledWith('/confirm_action', expect.anything());
    expect(chatMessages[chatMessages.length-1].content).toMatch(/cancelled/i);
    expect(appModule.pendingConfirmation).toBeNull();
  });
}); 
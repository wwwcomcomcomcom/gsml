const KEY = "jwt";

export const authStore = {
  get: () => localStorage.getItem(KEY),
  set: (token: string) => localStorage.setItem(KEY, token),
  clear: () => localStorage.removeItem(KEY),
  isAuthed: () => !!localStorage.getItem(KEY),
};

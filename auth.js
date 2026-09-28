const supabaseClient = supabase.createClient(
  window.CRYPTOENGINEER_SUPABASE_URL,
  window.CRYPTOENGINEER_SUPABASE_KEY,
  { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true } }
);

async function currentUser() {
  const { data } = await supabaseClient.auth.getUser();
  return data?.user || null;
}

async function requireUser(redirect = 'auth.html') {
  const user = await currentUser();
  if (!user) {
    window.location.href = redirect + '?next=' + encodeURIComponent(location.pathname + location.search);
    return null;
  }
  return user;
}

async function isAdmin() {
  const user = await currentUser();
  if (!user) return false;
  const { data } = await supabaseClient.from('profiles').select('role').eq('id', user.id).maybeSingle();
  return data?.role === 'admin';
}

async function signOut() {
  await supabaseClient.auth.signOut();
  location.href = 'index.html';
}

async function refreshAuthUI() {
  const user = await currentUser();
  document.querySelectorAll('[data-auth]').forEach(el => el.style.display = user ? '' : 'none');
  document.querySelectorAll('[data-guest]').forEach(el => el.style.display = user ? 'none' : '');
  document.querySelectorAll('[data-user-email]').forEach(el => el.textContent = user?.email || '');
  if (user && await isAdmin()) document.querySelectorAll('[data-admin]').forEach(el => el.style.display = '');
}

window.CryptoAuth = { supabaseClient, currentUser, requireUser, isAdmin, signOut, refreshAuthUI };

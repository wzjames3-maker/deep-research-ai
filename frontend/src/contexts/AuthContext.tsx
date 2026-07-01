import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { authApi } from "@/api/auth";

interface AuthState {
  token: string | null;
  username: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

// Storage helper: use sessionStorage if rememberMe=false, localStorage otherwise
function getStorage(rememberMe: boolean): Storage {
  return rememberMe ? localStorage : sessionStorage;
}

function getToken(): string | null {
  return localStorage.getItem("token") || sessionStorage.getItem("token");
}

function getUsername(): string | null {
  return localStorage.getItem("username") || sessionStorage.getItem("username");
}

function clearAllStorage() {
  localStorage.clear();
  sessionStorage.clear();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: getToken(),
    username: getUsername(),
    isAuthenticated: !!getToken(),
    isLoading: true,
  });

  // Hydrate: verify token on app startup
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setState((s) => ({ ...s, isLoading: false }));
      return;
    }
    authApi
      .getMe()
      .then((me) => {
        // Keep token in whichever storage it was in
        const storage = localStorage.getItem("token") ? localStorage : sessionStorage;
        storage.setItem("username", me.username);
        setState({
          token,
          username: me.username,
          isAuthenticated: true,
          isLoading: false,
        });
      })
      .catch(() => {
        clearAllStorage();
        setState({
          token: null,
          username: null,
          isAuthenticated: false,
          isLoading: false,
        });
      });
  }, []);

  const login = useCallback(
    async (username: string, password: string, rememberMe = false) => {
      const resp = await authApi.login(username, password, rememberMe);
      const storage = getStorage(rememberMe);
      // Clear the other storage first
      (rememberMe ? sessionStorage : localStorage).removeItem("token");
      (rememberMe ? sessionStorage : localStorage).removeItem("username");
      storage.setItem("token", resp.token);
      storage.setItem("username", resp.username);
      setState({
        token: resp.token,
        username: resp.username,
        isAuthenticated: true,
        isLoading: false,
      });
    },
    []
  );

  const register = useCallback(async (username: string, password: string) => {
    const resp = await authApi.register(username, password);
    localStorage.setItem("token", resp.token);
    localStorage.setItem("username", resp.username);
    setState({
      token: resp.token,
      username: resp.username,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const logout = useCallback(() => {
    clearAllStorage();
    setState({
      token: null,
      username: null,
      isAuthenticated: false,
      isLoading: false,
    });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used within AuthProvider");
  return ctx;
}

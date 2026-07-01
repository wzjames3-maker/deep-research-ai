import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuthContext } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Search } from "lucide-react";

const USERNAME_RE = /^[a-zA-Z0-9_]+$/;

function validateUsername(v: string): string | null {
  if (v.length < 3) return "用户名至少 3 个字符";
  if (v.length > 50) return "用户名最多 50 个字符";
  if (!USERNAME_RE.test(v)) return "用户名仅支持字母、数字和下划线";
  return null;
}

function validatePassword(v: string): string | null {
  if (v.length < 8) return "密码至少 8 个字符";
  if (v.length > 64) return "密码最多 64 个字符";
  if (!/[a-zA-Z]/.test(v)) return "密码需包含至少 1 个字母";
  if (!/[0-9]/.test(v)) return "密码需包含至少 1 个数字";
  return null;
}

export default function RegisterPage() {
  const { register } = useAuthContext();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPwd, setConfirmPwd] = useState("");
  const [loading, setLoading] = useState(false);
  const [touched, setTouched] = useState({ username: false, password: false, confirm: false });

  const usernameErr = touched.username ? validateUsername(username) : null;
  const passwordErr = touched.password ? validatePassword(password) : null;
  const confirmErr = touched.confirm && confirmPwd !== password ? "两次密码不一致" : null;

  const isValid =
    !validateUsername(username) &&
    !validatePassword(password) &&
    confirmPwd === password &&
    !loading;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setTouched({ username: true, password: true, confirm: true });
    if (!isValid) return;
    setLoading(true);
    try {
      await register(username, password);
      toast.success("注册成功，已自动登录");
      navigate("/dashboard");
    } catch (err: unknown) {
      const error = err as { response?: { status: number; data?: { code?: string; message?: string } } };
      const status = error.response?.status;
      const code = error.response?.data?.code;
      if (status === 409 || code === "USERNAME_EXISTS") {
        toast.error("用户名已被注册");
      } else if (status === 429 || code === "RATE_LIMITED") {
        toast.error("操作过于频繁，请稍后再试");
      } else {
        toast.error(error.response?.data?.message || "注册失败");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-4xl grid md:grid-cols-2 gap-8 items-center">
        {/* Left: Hero */}
        <div className="hidden md:flex flex-col items-center justify-center text-center space-y-4">
          <div className="w-32 h-32 rounded-full bg-primary/10 flex items-center justify-center">
            <Search className="w-16 h-16 text-primary" />
          </div>
          <h1 className="text-3xl font-bold">DeepResearch</h1>
          <p className="text-muted-foreground max-w-sm">
            注册账号，开始你的自动化深度研究之旅
          </p>
        </div>

        {/* Right: Form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">注册</CardTitle>
            <CardDescription>创建新账号</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">用户名</Label>
                <Input
                  id="username"
                  placeholder="3-50 字符，字母/数字/下划线"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, username: true }))}
                  autoComplete="username"
                  autoFocus
                />
                {usernameErr && <p className="text-sm text-destructive">{usernameErr}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="8-64 字符，至少 1 字母 + 1 数字"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, password: true }))}
                  autoComplete="new-password"
                />
                {passwordErr && <p className="text-sm text-destructive">{passwordErr}</p>}
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirmPwd">确认密码</Label>
                <Input
                  id="confirmPwd"
                  type="password"
                  placeholder="再次输入密码"
                  value={confirmPwd}
                  onChange={(e) => setConfirmPwd(e.target.value)}
                  onBlur={() => setTouched((t) => ({ ...t, confirm: true }))}
                  autoComplete="new-password"
                />
                {confirmErr && <p className="text-sm text-destructive">{confirmErr}</p>}
              </div>
              <Button type="submit" className="w-full" disabled={!isValid}>
                {loading && <Loader2 className="animate-spin" />}
                {loading ? "注册中..." : "注册"}
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                已有账号？{" "}
                <Link to="/login" className="text-primary hover:underline">
                  去登录
                </Link>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

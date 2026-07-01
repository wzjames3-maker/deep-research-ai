import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuthContext } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, Search } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuthContext();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [loading, setLoading] = useState(false);

  const canSubmit = username.length >= 3 && password.length >= 8 && !loading;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    try {
      await login(username, password, rememberMe);
      toast.success("登录成功");
      navigate("/dashboard");
    } catch (err: unknown) {
      const error = err as { response?: { status: number; data?: { code?: string; message?: string } } };
      const status = error.response?.status;
      const code = error.response?.data?.code;
      if (status === 401) {
        toast.error("用户名或密码错误");
      } else if (status === 423 || code === "ACCOUNT_LOCKED") {
        toast.error("账户已锁定，请稍后再试");
      } else if (status === 429 || code === "RATE_LIMITED") {
        toast.error("操作过于频繁，请稍后再试");
      } else {
        toast.error(error.response?.data?.message || "登录失败");
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
            自动化深度研究智能体 — 输入主题，AI 自动搜索、分析、生成研究报告
          </p>
        </div>

        {/* Right: Form */}
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">登录</CardTitle>
            <CardDescription>输入账号和密码登录工作台</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">用户名</Label>
                <Input
                  id="username"
                  placeholder="请输入用户名"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">密码</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="请输入密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="remember"
                  checked={rememberMe}
                  onCheckedChange={(v) => setRememberMe(v === true)}
                />
                <Label htmlFor="remember" className="text-sm font-normal cursor-pointer">
                  记住登录
                </Label>
              </div>
              <Button type="submit" className="w-full" disabled={!canSubmit}>
                {loading && <Loader2 className="animate-spin" />}
                {loading ? "登录中..." : "登录"}
              </Button>
              <p className="text-center text-sm text-muted-foreground">
                没有账号？{" "}
                <Link to="/register" className="text-primary hover:underline">
                  去注册
                </Link>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import { useState } from "react"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Toaster, toast } from "@/components/ui/toast"
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "@/components/ui/table"

interface Divergencia {
  numero_sistema: string | null
  aluno_sistema: string
  disciplina: string
  campo: string
  nota_sistema: string
  nota_fisica: string
}

interface GrupoAluno {
  numero: string | null
  aluno: string
  itens: Divergencia[]
}

function agruparPorAluno(divergencias: Divergencia[]): GrupoAluno[] {
  const mapa = new Map<string, GrupoAluno>()
  for (const d of divergencias) {
    if (!mapa.has(d.aluno_sistema)) {
      mapa.set(d.aluno_sistema, { numero: d.numero_sistema, aluno: d.aluno_sistema, itens: [] })
    }
    mapa.get(d.aluno_sistema)!.itens.push(d)
  }
  return Array.from(mapa.values())
}

function App() {
  const [arquivoSistema, setArquivoSistema] = useState<File | null>(null)
  const [arquivoFisica, setArquivoFisica] = useState<File | null>(null)
  const [grupos, setGrupos] = useState<GrupoAluno[]>([])
  const [totalFalhasLeitura, setTotalFalhasLeitura] = useState(0)
  const [carregando, setCarregando] = useState(false)
  const [gerandoPdf, setGerandoPdf] = useState(false)

  function montarFormData() {
    const formData = new FormData()
    formData.append("pdf_sistema", arquivoSistema!)
    formData.append("pauta_fisica", arquivoFisica!)
    return formData
  }

  async function handleVerificar() {
    if (!arquivoSistema || !arquivoFisica) {
      toast.add({
        title: "Faltam arquivos",
        description: "Selecione o PDF do sistema e a pauta física antes de verificar.",
        type: "error",
      })
      return
    }

    setCarregando(true)
    try {
      const resposta = await fetch("http://127.0.0.1:8000/comparar", {
        method: "POST",
        body: montarFormData(),
      })
      if (!resposta.ok) throw new Error(`Erro do servidor: ${resposta.status}`)

      const dados = await resposta.json()
      setGrupos(agruparPorAluno(dados.divergencias_reais))
      setTotalFalhasLeitura(dados.falhas_leitura.length)

      toast.add({
        title: "Verificação concluída",
        description: `${dados.divergencias_reais.length} divergência(s) real(is) em ${agruparPorAluno(dados.divergencias_reais).length} aluno(s).`,
        type: dados.divergencias_reais.length > 0 ? "warning" : "success",
      })
    } catch (erro) {
      toast.add({ title: "Erro ao verificar", description: String(erro), type: "error" })
    } finally {
      setCarregando(false)
    }
  }

  async function handleGerarPdf() {
    if (!arquivoSistema || !arquivoFisica) {
      toast.add({
        title: "Faltam arquivos",
        description: "Selecione os arquivos antes de gerar o relatório.",
        type: "error",
      })
      return
    }

    setGerandoPdf(true)
    try {
      const resposta = await fetch("http://127.0.0.1:8000/relatorio", {
        method: "POST",
        body: montarFormData(),
      })
      if (!resposta.ok) throw new Error(`Erro do servidor: ${resposta.status}`)

      const blob = await resposta.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = "relatorio_pauta.pdf"
      link.click()
      window.URL.revokeObjectURL(url)
    } catch (erro) {
      toast.add({ title: "Erro ao gerar PDF", description: String(erro), type: "error" })
    } finally {
      setGerandoPdf(false)
    }
  }

  return (
    <div className="flex min-h-svh flex-col items-center gap-6 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Verificar Pauta</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="pdf-sistema">Pauta do sistema (PDF)</Label>
            <Input id="pdf-sistema" type="file" accept=".pdf"
              onChange={(e) => setArquivoSistema(e.target.files?.[0] ?? null)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="pauta-fisica">Pauta física (PNG ou JPEG)</Label>
            <Input id="pauta-fisica" type="file" accept=".png,.jpg,.jpeg"
              onChange={(e) => setArquivoFisica(e.target.files?.[0] ?? null)} />
          </div>
          <Button className="w-full" onClick={handleVerificar} disabled={carregando}>
            {carregando ? "Verificando..." : "Verificar"}
          </Button>
          <Button className="w-full" variant="outline" onClick={handleGerarPdf} disabled={gerandoPdf}>
            {gerandoPdf ? "Gerando PDF..." : "Gerar Relatório PDF"}
          </Button>
        </CardContent>
      </Card>

      {totalFalhasLeitura > 0 && (
        <p className="text-sm text-muted-foreground max-w-2xl text-center">
          {totalFalhasLeitura} célula(s) não foram lidas com confiança pelo OCR e não entraram na
          lista abaixo — aparecem detalhadas no relatório PDF.
        </p>
      )}

      {grupos.map((grupo) => (
        <Card key={grupo.aluno} className="w-full max-w-4xl">
          <CardHeader>
            <CardTitle>
              {grupo.numero ? `Nº ${grupo.numero} — ` : ""}{grupo.aluno}
              <span className="text-muted-foreground font-normal text-sm ml-2">
                ({grupo.itens.length} divergência{grupo.itens.length > 1 ? "s" : ""})
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Disciplina</TableHead>
                  <TableHead>Campo</TableHead>
                  <TableHead>Nota Sistema</TableHead>
                  <TableHead>Nota Física</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {grupo.itens.map((d, i) => (
                  <TableRow key={i}>
                    <TableCell>{d.disciplina}</TableCell>
                    <TableCell>{d.campo}</TableCell>
                    <TableCell>{d.nota_sistema}</TableCell>
                    <TableCell>{d.nota_fisica}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ))}

      <Toaster />
    </div>
  )
}

export default App
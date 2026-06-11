# Guia de Contribuicao

Obrigado pelo interesse em contribuir com o **Crypto Fraud Tracker**! Contribuicoes
sao muito bem-vindas, sejam correcoes de bugs, novas funcionalidades, melhorias na
documentacao ou novos indicadores de comprometimento (IOCs).

## Como contribuir

1. **Faca um fork** do repositorio
2. **Crie uma branch** para sua mudanca:
   ```bash
   git checkout -b feature/minha-melhoria
   ```
3. **Faca suas alteracoes** seguindo os padroes do projeto (veja abaixo)
4. **Garanta que os testes passam** (obrigatorio):
   ```bash
   docker-compose exec backend python -m pytest tests/ -v
   ```
5. **Adicione testes** para qualquer nova funcionalidade ou correcao
6. **Faca commit** com mensagens descritivas:
   ```bash
   git commit -m "feat: descreve a mudanca"
   ```
7. **Envie um Pull Request** para a branch `main`

## Requisitos para aprovacao

Todo Pull Request precisa atender a:

- **Todos os 28 testes passando** (`pytest tests/ -v`)
- **Testes novos** cobrindo o codigo adicionado
- **Revisao e aprovacao do mantenedor** antes do merge
- Sem segredos, senhas ou credenciais no codigo (use variaveis de ambiente)
- Codigo que compila e roda no ambiente Docker do projeto

## Padroes do projeto

- **Backend**: Python, FastAPI. Mantenha as queries SQL parametrizadas.
- **Edicoes cirurgicas**: prefira mudancas pequenas e focadas a grandes reescritas.
- **Validacao**: scripts e codigo devem validar entradas (ex: `py_compile`).
- **Seguranca**: nunca commite o arquivo `.env` nem credenciais. Use o `.env.example`
  como referencia das variaveis necessarias.
- **IOCs**: ao adicionar enderecos de carteiras, **cite a fonte publica confiavel**
  (OFAC, CISA, relatorios de threat intelligence). Nunca adicione enderecos sem fonte.

## Reportar bugs ou sugerir melhorias

Abra uma **issue** no GitHub descrevendo:

- O que aconteceu (e o que era esperado)
- Passos para reproduzir
- Ambiente (SO, versao do Docker)
- Logs relevantes (sem incluir segredos!)

## Contato

Duvidas sobre contribuicoes podem ser direcionadas ao mantenedor:

- **Email**: to.brunoaugusto@yahoo.com.br
- **LinkedIn**: https://www.linkedin.com/in/bruno-augusto-lobo-soares/

## Codigo de Conduta

Seja respeitoso e construtivo. Este e um espaco colaborativo voltado para pesquisa
legitima em seguranca, compliance e deteccao de fraude. Contribuicoes que promovam
uso malicioso da ferramenta nao serao aceitas.

---
Obrigado por ajudar a melhorar o Crypto Fraud Tracker!

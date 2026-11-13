from django.contrib.auth import authenticate, login as entrar, logout as deslogar
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from UniRideSite.models import Aluno, Avaliacao, Solicitacao, Trajeto
from django.contrib import messages
from django.views.decorators.http import require_POST

def login(request):
    '''Tela 1 - Login: confere e-mail e senha e abre a sessão do aluno.'''
    erro = None
    if request.method == 'POST':
        user = authenticate(request, username=request.POST['email'], password=request.POST['senha'])
        if user is not None:
            entrar(request, user)
            return redirect('home')
        erro = 'E-mail ou senha incorretos.'
    return render(request, 'login.html', {'erro': erro})


def criar_conta(request):
    '''Tela 1.1 - Criar conta: cria o usuário de login e o aluno ligado a ele.'''
    erros = []
    if request.method == 'POST':
        nome = request.POST['nome'].strip()
        email = request.POST['email'].strip().lower()
        matricula = request.POST['matricula'].strip()
        curso = request.POST['curso'].strip()
        senha = request.POST['senha']
        senha2 = request.POST['senha2']

        if not email.endswith('@puc-rio.br'):
            erros.append('Use seu e-mail institucional (@puc-rio.br).')
        if User.objects.filter(username=email).exists() or Aluno.objects.filter(email=email).exists():
            erros.append('Já existe uma conta com este e-mail.')
        if Aluno.objects.filter(matricula=matricula).exists():
            erros.append('Já existe uma conta com esta matrícula.')
        if len(senha) < 8:
            erros.append('A senha precisa ter pelo menos 8 caracteres.')
        if senha != senha2:
            erros.append('As senhas não são iguais.')
        if 'termos' not in request.POST:
            erros.append('É preciso aceitar os Termos de uso.')

        if not erros:
            # transaction.atomic: se der erro ao criar o aluno, o usuário também não é salvo
            with transaction.atomic():
                user = User.objects.create_user(username=email, email=email, password=senha)
                Aluno.objects.create(user=user, nome=nome, email=email, matricula=matricula, curso=curso)
            entrar(request, user)
            return redirect('home')
    return render(request, 'criar-conta.html', {'erros': erros})


def sair(request):
    '''Encerra a sessão e volta para o login.'''
    deslogar(request)
    return redirect('login')


@login_required
def home(request):
    '''Tela 2 - Início: mostra o trajeto do aluno.'''
    return render(request, 'home.html')


@login_required
def cadastrar_trajeto(request):
    '''Tela 3 - Cadastrar ou editar o trajeto.'''
    return render(request, 'cadastrar-trajeto.html')


@login_required
def caronas_encontradas(request):
    '''Tela 4 - Lista de caronas compatíveis com o trajeto.'''
    caronas = Trajeto.objects.filter(tipo=Trajeto.OFERECE, ativo=True).annotate(
        nota=Avg('aluno__avaliacoes_recebidas__estrelas')
    )
    return render(request, 'caronas-encontradas.html', {'caronas': caronas})

@login_required
def detalhes_carona(request, id):
    '''Tela 5 - Detalhes de uma carona.'''
    carona = get_object_or_404(Trajeto, id=id)
    nota = Avaliacao.objects.filter(avaliado=carona.aluno).aggregate(media=Avg('estrelas'))['media']
    total_caronas = Solicitacao.objects.filter(trajeto__aluno=carona.aluno, status=Solicitacao.ACEITA).count()
    return render(request, 'detalhes-carona.html', {'carona': carona, 'nota': nota, 'total_caronas': total_caronas})


@login_required
def minhas_caronas(request):
    '''Tela 6 - Caronas do aluno (ativas e solicitações).'''
    aluno = aluno_temporario(request)

    # Pedidos que o aluno fez como passageiro (já traz o motorista junto)
    pedidos = aluno.solicitacoes.select_related('trajeto__aluno')

    contexto = {
        'aluno': aluno,
        'caronas_aceitas': pedidos.filter(status=Solicitacao.ACEITA),
        'pedidos_pendentes': pedidos.filter(status=Solicitacao.PENDENTE),
        'pedidos_recusados': pedidos.filter(status=Solicitacao.RECUSADA),
    }

        # Se o aluno oferece carona, busca os pedidos recebidos no trajeto dele
    trajeto_motorista = aluno.trajetos.filter(tipo=Trajeto.OFERECE, ativo=True).first()
    if trajeto_motorista:
        recebidos = trajeto_motorista.solicitacoes.select_related('passageiro')
        contexto['trajeto_motorista'] = trajeto_motorista
        contexto['pedidos_recebidos'] = recebidos.filter(status=Solicitacao.PENDENTE)
        contexto['passageiros_confirmados'] = recebidos.filter(status=Solicitacao.ACEITA)
   
    return render(request, 'minhas-caronas.html', contexto)


@login_required
def perfil(request):
    '''Tela 7 - Perfil do aluno.'''
    return render(request,'perfil.html')

@login_required
def editar_perfil(request):
    '''Tela 7.1 - Editar perfil: salva nome e curso do aluno.'''
    aluno = aluno_temporario(request)
    if request.method == 'POST':
        aluno.nome = request.POST['nome']
        aluno.curso = request.POST['curso']
        aluno.save()
        return redirect('perfil')
    trajeto = aluno.trajetos.first()
    return render(request, 'editar-perfil.html', {'aluno': aluno, 'trajeto': trajeto})

@login_required
def solicitar_carona(request, id):
    '''Cria um pedido de carona (PENDENTE) para o trajeto escolhido.'''
    carona = get_object_or_404(Trajeto, id=id)
    if request.method == 'POST':
        passageiro = aluno_temporario(request)
        Solicitacao.objects.get_or_create(trajeto=carona, passageiro=passageiro)
    return redirect(reverse('detalhes-carona', args=[id]) + '#enviado')

def termos(request):
    '''Termos de Uso. Página pública: não colocar @login_required (o cadastro aponta para ela).'''
    return render(request, 'termos.html')

def recuperar_senha(request):
    '''Recuperar senha. Página pública: não colocar @login_required.'''
    return render(request, 'recuperar-senha.html')

def aluno_temporario(request):
    '''Devolve o aluno logado (ligado ao usuário do Django).'''
    return request.user.aluno

@login_required
@require_POST
def responder_solicitacao(request, id):
    '''O motorista aceita ou recusa um pedido de carona (B5).'''
    solicitacao = get_object_or_404(Solicitacao, id=id)
    trajeto = solicitacao.trajeto
    aluno = aluno_temporario(request)
    acao = request.POST.get('acao')

    # Só o dono do trajeto pode responder
    if trajeto.aluno != aluno:
        messages.error(request, 'Você só pode responder pedidos da sua própria carona.')
        return redirect('minhas-caronas')

    # Só pedidos que ainda estão esperando resposta
    if solicitacao.status != Solicitacao.PENDENTE:
        messages.error(request, 'Este pedido já foi respondido.')
        return redirect('minhas-caronas')

    if acao == 'aceitar':
        aceitas = trajeto.solicitacoes.filter(status=Solicitacao.ACEITA).count()
        if aceitas >= trajeto.vagas:
            messages.error(request, 'Sua carona não tem mais vagas.')
            return redirect('minhas-caronas')
        solicitacao.status = Solicitacao.ACEITA
        solicitacao.save()
        messages.success(request, f'{solicitacao.passageiro.nome} entrou na sua carona!')
    elif acao == 'recusar':
        solicitacao.status = Solicitacao.RECUSADA
        solicitacao.save()
        messages.success(request, f'Pedido de {solicitacao.passageiro.nome} recusado.')
    else:
        messages.error(request, 'Ação inválida.')

    return redirect('minhas-caronas')
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from UniRideSite.models import Aluno, Avaliacao, Solicitacao, Trajeto


def criar_aluno(nome, email, matricula):
    user = User.objects.create_user(username=email, email=email, password='uniride123')
    return Aluno.objects.create(user=user, nome=nome, email=email, matricula=matricula, curso='Teste')


class ResponderSolicitacaoTests(TestCase):
    '''B5: o motorista aceita ou recusa pedidos da própria carona.'''

    def setUp(self):
        self.motorista = criar_aluno('Mariana', 'mariana@teste.com', '1')
        self.passageiro = criar_aluno('Bernardo', 'bernardo@teste.com', '2')
        self.outro = criar_aluno('Joao', 'joao@teste.com', '3')
        self.trajeto = Trajeto.objects.create(aluno=self.motorista, tipo=Trajeto.OFERECE,
                                              origem='Copacabana', horario='07:00', vagas=1, seg=True)
        self.pedido = Solicitacao.objects.create(trajeto=self.trajeto, passageiro=self.passageiro)
        self.url = reverse('responder-solicitacao', args=[self.pedido.id])

    def responder(self, email, acao):
        self.client.login(username=email, password='uniride123')
        return self.client.post(self.url, {'acao': acao})

    def status(self):
        self.pedido.refresh_from_db()
        return self.pedido.status

    def test_motorista_aceita(self):
        r = self.responder('mariana@teste.com', 'aceitar')
        self.assertRedirects(r, reverse('minhas-caronas'))
        self.assertEqual(self.status(), Solicitacao.ACEITA)

    def test_motorista_recusa(self):
        self.responder('mariana@teste.com', 'recusar')
        self.assertEqual(self.status(), Solicitacao.RECUSADA)

    def test_quem_nao_e_dono_nao_responde(self):
        self.responder('joao@teste.com', 'aceitar')
        self.assertEqual(self.status(), Solicitacao.PENDENTE)

    def test_nao_aceita_sem_vaga(self):
        Solicitacao.objects.create(trajeto=self.trajeto, passageiro=self.outro, status=Solicitacao.ACEITA)
        self.responder('mariana@teste.com', 'aceitar')
        self.assertEqual(self.status(), Solicitacao.PENDENTE)

    def test_pedido_ja_respondido_nao_muda(self):
        self.pedido.status = Solicitacao.RECUSADA
        self.pedido.save()
        self.responder('mariana@teste.com', 'aceitar')
        self.assertEqual(self.status(), Solicitacao.RECUSADA)

    def test_get_nao_e_permitido(self):
        self.client.login(username='mariana@teste.com', password='uniride123')
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)
        self.assertEqual(self.status(), Solicitacao.PENDENTE)

    def test_deslogado_vai_para_login(self):
        r = self.client.post(self.url, {'acao': 'aceitar'})
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r['Location'])
        self.assertEqual(self.status(), Solicitacao.PENDENTE)


class CriarContaTests(TestCase):
    '''Bloco A - parte 3: cadastro de aluno com e-mail institucional.'''

    def dados(self, **mudancas):
        d = {'nome': 'Maria Silva', 'email': 'maria@puc-rio.br', 'matricula': '2410001',
             'curso': 'Direito', 'senha': 'senhaforte', 'senha2': 'senhaforte', 'termos': 'on'}
        d.update(mudancas)
        return d

    def test_cria_usuario_e_aluno_e_entra(self):
        r = self.client.post(reverse('criar-conta'), self.dados())
        self.assertRedirects(r, reverse('home'))
        aluno = Aluno.objects.get(email='maria@puc-rio.br')
        self.assertEqual(aluno.user.username, 'maria@puc-rio.br')
        self.assertTrue(self.client.login(username='maria@puc-rio.br', password='senhaforte'))

    def test_recusa_email_fora_da_puc(self):
        self.client.post(reverse('criar-conta'), self.dados(email='maria@gmail.com'))
        self.assertFalse(Aluno.objects.exists())
        self.assertFalse(User.objects.exists())

    def test_recusa_senhas_diferentes(self):
        self.client.post(reverse('criar-conta'), self.dados(senha2='outrasenha'))
        self.assertFalse(Aluno.objects.exists())

    def test_recusa_email_ou_matricula_repetidos(self):
        criar_aluno('Joao', 'joao@puc-rio.br', '2410009')
        self.client.post(reverse('criar-conta'), self.dados(email='joao@puc-rio.br'))
        self.client.post(reverse('criar-conta'), self.dados(matricula='2410009'))
        self.assertEqual(Aluno.objects.count(), 1)

    def test_recusa_sem_aceitar_termos(self):
        dados = self.dados()
        del dados['termos']
        self.client.post(reverse('criar-conta'), dados)
        self.assertFalse(Aluno.objects.exists())


class AvaliarUsuarioTests(TestCase):
    '''Bloco 1: depois de uma carona aceita, passageiro e motorista se avaliam.'''

    def setUp(self):
        self.motorista = criar_aluno('Ana', 'ana@teste.com', '1')
        self.passageiro = criar_aluno('Joao', 'joao@teste.com', '2')
        self.outro = criar_aluno('Bernardo', 'bernardo@teste.com', '3')
        trajeto = Trajeto.objects.create(aluno=self.motorista, tipo=Trajeto.OFERECE,
                                         origem='Botafogo', horario='07:20', vagas=2, seg=True)
        self.carona = Solicitacao.objects.create(trajeto=trajeto, passageiro=self.passageiro,
                                                 status=Solicitacao.ACEITA)
        self.url = reverse('avaliar-usuario', args=[self.carona.id])

    def avaliar(self, email, estrelas='4'):
        self.client.login(username=email, password='uniride123')
        return self.client.post(self.url, {'estrelas': estrelas, 'comentario': 'Tudo certo'})

    def test_motorista_avalia_passageiro_e_nota_do_perfil_muda(self):
        r = self.avaliar('ana@teste.com', '4')
        self.assertRedirects(r, self.url)
        avaliacao = Avaliacao.objects.get()
        self.assertEqual(avaliacao.avaliado, self.passageiro)
        self.assertEqual(avaliacao.estrelas, 4)
        # A nota do Perfil é a média das avaliações recebidas
        self.client.login(username='joao@teste.com', password='uniride123')
        self.assertEqual(self.client.get(reverse('perfil')).context['nota'], 4)

    def test_passageiro_avalia_motorista(self):
        self.client.login(username='joao@teste.com', password='uniride123')
        self.client.post(self.url, {'estrelas': '5', 'comentario': 'Tudo certo', 'destaques': 'Pontualidade'})
        avaliacao = Avaliacao.objects.get()
        self.assertEqual(avaliacao.avaliado, self.motorista)
        self.assertEqual(avaliacao.comentario, 'Destaques: Pontualidade. Tudo certo')

    def test_quem_nao_participou_recebe_404(self):
        r = self.avaliar('bernardo@teste.com')
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Avaliacao.objects.exists())

    def test_carona_nao_aceita_nao_pode_ser_avaliada(self):
        self.carona.status = Solicitacao.PENDENTE
        self.carona.save()
        r = self.avaliar('ana@teste.com')
        self.assertRedirects(r, reverse('minhas-caronas'))
        self.assertFalse(Avaliacao.objects.exists())

    def test_avaliar_duas_vezes_mantem_a_primeira(self):
        self.avaliar('ana@teste.com', '4')
        self.avaliar('ana@teste.com', '1')
        self.assertEqual(Avaliacao.objects.count(), 1)
        self.assertEqual(Avaliacao.objects.get().estrelas, 4)

    def test_nota_fora_de_1_a_5_nao_e_salva(self):
        r = self.avaliar('ana@teste.com', '7')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Avaliacao.objects.exists())

    def test_deslogado_vai_para_login(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r['Location'])

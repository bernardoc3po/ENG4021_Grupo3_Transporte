import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'UniRideSite.settings')
django.setup()

from UniRideSite.models import Aluno, Veiculo, Trajeto, Solicitacao, Avaliacao

Avaliacao.objects.all().delete()
Solicitacao.objects.all().delete()
Trajeto.objects.all().delete()
Veiculo.objects.all().delete()
Aluno.objects.all().delete()
print('Tabelas limpas.')

print('Alunos no banco:', Aluno.objects.count())
print('Veiculos no banco:', Veiculo.objects.count())
print('Trajetos no banco:', Trajeto.objects.count())
print('Solicitacoes no banco:', Solicitacao.objects.count())
print('Avaliacoes no banco:', Avaliacao.objects.count())


bernardo = Aluno.objects.create(nome='Bernardo', email='bernardo@teste.com', matricula='2310001', curso='Engenharia de Producao')
ana = Aluno.objects.create(nome='Ana', email='ana@teste.com', matricula='2310002', curso='Engenharia Civil')
lucas = Aluno.objects.create(nome='Lucas', email='lucas@teste.com', matricula='2310003', curso='Administracao')
mariana = Aluno.objects.create(nome='Mariana', email='mariana@teste.com', matricula='2310004', curso='Direito')
joao = Aluno.objects.create(nome='Joao', email='joao@teste.com', matricula='2310005', curso='Engenharia de Producao')
sofia = Aluno.objects.create(nome='Sofia', email='sofia@teste.com', matricula='2310006', curso='Psicologia')
print('Alunos criados.')

#criar os veiculos (so quem oferece carona tem carro)
Veiculo.objects.create(motorista=ana, placa='ABC1D23', modelo='Chevrolet Onix', cor='Branco')
Veiculo.objects.create(motorista=lucas, placa='EFG4H56', modelo='Hyundai HB20', cor='Prata')
Veiculo.objects.create(motorista=mariana, placa='IJK7L89', modelo='Volkswagen Gol', cor='Preto')
print('Veiculos criados.')

#criar os trajetos
#quem oferece carona
trajeto_ana = Trajeto.objects.create(aluno=ana, tipo=Trajeto.OFERECE, origem='Botafogo', horario='07:30', vagas=3, seg=True, qua=True, sex=True)
trajeto_lucas = Trajeto.objects.create(aluno=lucas, tipo=Trajeto.OFERECE, origem='Tijuca', horario='08:00', vagas=2, ter=True, qui=True)
trajeto_mariana = Trajeto.objects.create(aluno=mariana, tipo=Trajeto.OFERECE, origem='Copacabana', horario='07:00', vagas=4, seg=True, ter=True, qua=True, qui=True, sex=True)
#quem procura carona
trajeto_bernardo = Trajeto.objects.create(aluno=bernardo, tipo=Trajeto.PROCURA, origem='Botafogo', horario='07:30', seg=True, qua=True, sex=True)
trajeto_joao = Trajeto.objects.create(aluno=joao, tipo=Trajeto.PROCURA, origem='Tijuca', horario='08:00', ter=True, qui=True)
trajeto_sofia = Trajeto.objects.create(aluno=sofia, tipo=Trajeto.PROCURA, origem='Copacabana', horario='07:00', seg=True, ter=True, qua=True, qui=True, sex=True)
print('Trajetos criados.')



#criar as solicitacoes (pedidos de carona)
# Pedidos aceitos
pedido_bernardo_ana = Solicitacao.objects.create(trajeto=trajeto_ana, passageiro=bernardo, status=Solicitacao.ACEITA)
pedido_joao_lucas = Solicitacao.objects.create(trajeto=trajeto_lucas, passageiro=joao, status=Solicitacao.ACEITA)
pedido_sofia_mariana = Solicitacao.objects.create(trajeto=trajeto_mariana, passageiro=sofia, status=Solicitacao.ACEITA)
#pedidos ainda sem resposta (o status PENDENTE)
Solicitacao.objects.create(trajeto=trajeto_mariana, passageiro=bernardo)
Solicitacao.objects.create(trajeto=trajeto_lucas, passageiro=sofia)
#pedido recusado
Solicitacao.objects.create(trajeto=trajeto_ana, passageiro=joao, status=Solicitacao.RECUSADA)
print('Solicitacoes criadas.')




#criar as avaliacoes (so de caronas aceitas) ----------
#carona de Bernardo com Ana
Avaliacao.objects.create(solicitacao=pedido_bernardo_ana, avaliador=bernardo, avaliado=ana, estrelas=5, comentario='Carona tranquila e pontual.')
Avaliacao.objects.create(solicitacao=pedido_bernardo_ana, avaliador=ana, avaliado=bernardo, estrelas=5, comentario='Passageiro educado e chegou na hora.')
#carona de Joao com Lucas
Avaliacao.objects.create(solicitacao=pedido_joao_lucas, avaliador=joao, avaliado=lucas, estrelas=4, comentario='Boa conversa, mas saiu um pouco atrasado.')
Avaliacao.objects.create(solicitacao=pedido_joao_lucas, avaliador=lucas, avaliado=joao, estrelas=5, comentario='Sem nenhum problema.')
#carona de Sofia com Mariana (sem comentario)
Avaliacao.objects.create(solicitacao=pedido_sofia_mariana, avaliador=sofia, avaliado=mariana, estrelas=5, comentario='Direção segura e carro limpo.')
Avaliacao.objects.create(solicitacao=pedido_sofia_mariana, avaliador=mariana, avaliado=sofia, estrelas=4)
print('Avaliacoes criadas.')
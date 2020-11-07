# genetic algorithm

import numpy as np
import pandas as pd
import random as rd
import matplotlib.pyplot as plt
from operator import itemgetter
from random import randint
from tqdm import tqdm


class GA:
    def __init__(self, population, n_generation, thresh, batch=20, convergence_rate=0.95, crossover_rate=0.25, crossover_point=0.5, mutation_rate=0.25, min_generation=0.5, plot=True):
        self.allreqs = population
        self.n_generation = n_generation
        self.thresh = thresh
        self.convergence_rate = convergence_rate
        self.crossover_rate = crossover_rate
        self.crossover_point = crossover_point
        self.mutation_rate = mutation_rate
        self.min_generation = min_generation
        self.plot = plot
        # initial population created randomly, shape is (batch, n_req)
        # e.g. initpop[0]
        # array([1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 1, 1,
        #        0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 1, 1, 0,
        #        1, 1, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 1,
        #        1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1,
        #        1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1])
        # initpop literal only true for initiation, subsequently it is no longer holding inital values
        self.initpop = np.array([[np.random.randint(2) for _ in range(len(population))] for r_ in range(batch)])
        # parent qty is half the offspring
        self.n_parent = int(batch / 2)
        self.n_offspring = batch - self.n_parent
        self.output = None

    def fitness(self):
        # population is group of masks (0/1) for which members of population is selected
        def get_score(select):
            # need pop and thresh from parent function
            slot_wise = np.array([self.allreqs[i] if s == 1 else np.zeros(self.allreqs.shape[1]) for i, s in enumerate(select)]).T
            sums = np.array([sum(s) for s in slot_wise])
            sums = 0 if np.any([sums > self.thresh]) else sum(sums)
            return sums
        scores = np.array(list(map(get_score, self.initpop))).astype(int)
        return scores 

    # parent
    def selection(self, f):
        f = list(f)
        parents = np.empty((self.n_parent, self.initpop.shape[1]))
        for i in range(self.n_parent):
            max_fitness_idx = np.where(f == np.max(f))
            parents[i,:] = self.initpop[max_fitness_idx[0][0], :]
            f[max_fitness_idx[0][0]] = 0
        return parents

    # offspring, crossover point is hardcoded as half
    def crossover(self, parents):
        # parents, n_offspring
        # parents.shape[1] is n_req
        offsprings = np.empty((self.n_offspring, parents.shape[1]))
        # crossover at half
        crossover_point = int(parents.shape[1] / 2)
        for i in range(self.n_offspring):
            # choose parent1, start from the fittest
            j = randint(0, int(parents.shape[0]/2))
            while j < parents.shape[0]:
                if rd.random() < self.crossover_rate:
                    j += 1
                    continue
                parent1_index = j % parents.shape[0]
                break
            else:
                parent1_index = 0
            j = randint(int(parents.shape[0]/2), parents.shape[0])
            # choose parent2, start from runner-up
            while j < parents.shape[0]:
                if rd.random() < self.crossover_rate:
                    j += 1
                    continue
                parent2_index = j % parents.shape[0]
                break
            else:
                parent2_index = 1
            # cross parents
            offsprings[i, :crossover_point] = parents[parent1_index, :crossover_point]
            offsprings[i, crossover_point:] = parents[parent2_index, crossover_point:]
        return offsprings

    def mutation(self, offsprings):
        mutants = np.empty((offsprings.shape))
        for i in range(mutants.shape[0]):
            mutants[i, :] = offsprings[i, :]
            if rd.random() > self.mutation_rate:
                # no mutation
                continue
            # mutate, toggle
            idx = randint(0, offsprings.shape[1] - 1) 
            mutants[i, idx] = 1 if mutants[i, idx] == 0 else 0
        return mutants

    def optimize(self):
        # reqs is allreqs
        # population is initpop
        # pop_size.shape is (batch, n_req)
        # num_generations is number of iterations
        # threshold is self explanatory
        parameters, fitness_history = [], []
        iterator = tqdm(range(self.n_generation)) if self.plot else range(self.n_generation)
        for i in iterator:
            # get scores
            f = self.fitness()
            fitness_history.append(f)
            # select group of fittest (high scoring) parents
            parents = self.selection(f)
            # cross parents for offsprings
            offsprings = self.crossover(parents)
            # mutate offsprings
            mutants = self.mutation(offsprings)
            # merge midway
            self.initpop[:self.n_parent, :] = parents
            self.initpop[self.n_offspring:, :] = mutants
            # early break
            cts = list(f).count(f.max())
            if f.max() != 0 and cts / f.shape[0] >= self.convergence_rate and i / self.n_generation >= self.min_generation:
                if self.plot:
                    print(f"Convergence at or above {round(self.convergence_rate * 100)}% after {i+1} generations")
                break
        else:
            # no convergence
            if self.plot:
                print('Not converging')
            
        fitness_last_gen = self.fitness()
        max_fitness = np.where(fitness_last_gen == np.max(fitness_last_gen))
        parameters.append(self.initpop[max_fitness[0][0], :])
        if self.plot:
            print('Last generation: \n{}\n'.format(self.initpop)) 
            print('Fitness of the last generation: \n{}\n'.format(fitness_last_gen))
        return parameters, fitness_history, i

    def execute(self):
        parameters, fitness_history, n_generation = self.optimize()
        if np.all(fitness_history[-1] == 0):
            self.output = None
            print('No solution. First gen may have been all zero')
            return None
        parameters = parameters[0]
        selected_items = np.where(parameters > 0)[0]
        if self.plot:
            print('The optimized parameters for the given inputs are: \n{}\n'.format(parameters))
            print('Accepted requests:', selected_items, '\n')
            fitness_history_mean = [np.mean(f) for f in fitness_history]
            fitness_history_max = [np.max(f) for f in fitness_history]
            plt.plot(list(range(n_generation+1)), fitness_history_mean, label='Mean Fitness')
            plt.plot(list(range(n_generation+1)), fitness_history_max, label='Max Fitness')
            plt.legend()
            plt.title('Fitness through the generations')
            plt.xlabel('Generations')
            plt.ylabel('Fitness')
            plt.show()
            print(np.asarray(fitness_history).shape)
            threshold_outlook = np.array([sum(trow) for trow in np.array([self.allreqs[i] for i in selected_items]).T]).astype(int)
            overall_outlook = np.array([sum(trow) for trow in self.allreqs.T]).astype(int)
            print('\nThreshold outlook:')
            for i, comparison in enumerate(['\trequest {},\taccepted {}'.format(*z) for z in zip(overall_outlook, threshold_outlook)]):
                print(i + 1, comparison)
            # score = sum(threshold_outlook) / sum([tcell if tcell <= self.thresh else self.thresh for tcell in overall_outlook])
            # print('\n{}% requests served'.format(round(100 * score)))
            print('\n{}% capacity\n'.format(round(100 * sum(threshold_outlook) / self.thresh / self.allreqs.shape[1])))
        self.output = selected_items
        return selected_items
